"""
Endpoints pour les patients et traitements
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.models.patient import (
    PatientConsentDraft,
    PatientEmailChallenge,
    PatientEmailGrant,
    PatientManagementSession,
    PatientTreatment,
)
from app.schemas.patient import (
    PatientConsentDraftCreate,
    PatientConsentDraftResponse,
    PatientConsentWithdrawal,
    PatientDeleteTreatments,
    PatientEmailVerificationConfirm,
    PatientEmailVerificationRequest,
    PatientEmailVerificationResult,
    PatientTreatmentCreate,
    PatientTreatmentResponse,
    PatientTreatmentUpdate,
    TreatmentStats,
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_medecin, require_admin
from sqlalchemy import desc, func, or_
from app.core.config import settings
from app.core.email import EmailDeliveryError, send_patient_verification_code
from app.core.rate_limiter import limiter

router = APIRouter()

OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_REQUESTS_PER_HOUR = 5
OTP_MAX_ATTEMPTS = 5
EMAIL_GRANT_LIFETIME = timedelta(minutes=20)
CONSENT_DRAFT_LIFETIME = timedelta(minutes=30)
MANAGEMENT_SESSION_LIFETIME = timedelta(minutes=30)


def _digest(value: str, purpose: str) -> str:
    key = settings.SECRET_KEY.encode("utf-8")
    message = f"{purpose}:{value}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _email_hash(email: str) -> str:
    return _digest(email.strip().lower(), "patient-email")


def _require_email_token(
    db: Session,
    email: str,
    token: str,
    now: datetime,
) -> PatientEmailGrant:
    email_hash = _email_hash(email)
    token_digest = _digest(token, "patient-registration-grant")
    grant = db.query(PatientEmailGrant).filter(
        PatientEmailGrant.email_hash == email_hash,
        PatientEmailGrant.token_digest == token_digest,
        PatientEmailGrant.expires_at > now,
    ).with_for_update().first()
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification is invalid or expired",
        )
    return grant


def _get_management_session(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> PatientManagementSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid management session is required",
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid management session is required",
        )
    management_session = db.query(PatientManagementSession).filter(
        PatientManagementSession.token_digest == _digest(token, "patient-management-session"),
        PatientManagementSession.expires_at > datetime.now(timezone.utc),
        PatientManagementSession.revoked_at.is_(None),
    ).first()
    if not management_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid management session is required",
        )
    return management_session


def _delete_treatments_for_session(
    db: Session,
    management_session: PatientManagementSession,
    treatment_ids: List[UUID],
) -> int:
    treatments = db.query(PatientTreatment).filter(
        PatientTreatment.id.in_(treatment_ids),
        PatientTreatment.contact_email == management_session.email,
    ).with_for_update().all()
    if len(treatments) != len(treatment_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more selected treatments are unavailable",
        )
    for treatment in treatments:
        db.delete(treatment)
    db.commit()
    return len(treatments)


@router.post(
    "/treatments/email-verification/request",
    response_model=PatientEmailVerificationResult,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20/minute")
def request_patient_email_verification(
    request: Request,
    verification_request: PatientEmailVerificationRequest,
    db: Session = Depends(get_db),
):
    """Send an OTP without revealing whether the email has any declarations."""
    now = datetime.now(timezone.utc)
    address_hash = _email_hash(str(verification_request.email))
    db.query(PatientEmailChallenge).filter(
        PatientEmailChallenge.created_at <= now - timedelta(hours=1),
    ).delete(synchronize_session=False)
    db.query(PatientEmailGrant).filter(
        PatientEmailGrant.expires_at <= now,
    ).delete(synchronize_session=False)
    db.query(PatientConsentDraft).filter(
        PatientConsentDraft.expires_at <= now,
    ).delete(synchronize_session=False)
    db.query(PatientManagementSession).filter(
        or_(
            PatientManagementSession.expires_at <= now,
            PatientManagementSession.revoked_at.is_not(None),
        ),
    ).delete(synchronize_session=False)
    recent = db.query(PatientEmailChallenge).filter(
        PatientEmailChallenge.email_hash == address_hash,
        PatientEmailChallenge.created_at >= now - timedelta(hours=1),
    ).order_by(PatientEmailChallenge.created_at.desc()).all()
    generic_message = (
        "Si l'adresse est valide et la demande autorisée, "
        "un code de vérification sera envoyé."
    )
    cooldown_active = db.query(PatientEmailChallenge.id).filter(
        PatientEmailChallenge.email_hash == address_hash,
        PatientEmailChallenge.purpose == verification_request.purpose,
        PatientEmailChallenge.created_at > now - OTP_RESEND_COOLDOWN,
    ).first() is not None

    if len(recent) >= OTP_MAX_REQUESTS_PER_HOUR or cooldown_active:
        db.commit()
        return PatientEmailVerificationResult(message=generic_message)

    db.query(PatientEmailChallenge).filter(
        PatientEmailChallenge.email_hash == address_hash,
        PatientEmailChallenge.purpose == verification_request.purpose,
        PatientEmailChallenge.consumed_at.is_(None),
    ).update({"consumed_at": now}, synchronize_session=False)

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = PatientEmailChallenge(
        email_hash=address_hash,
        purpose=verification_request.purpose,
        code_digest=_digest(f"{address_hash}:{code}", "patient-email-otp"),
        expires_at=now + OTP_LIFETIME,
    )
    db.add(challenge)
    db.commit()

    try:
        send_patient_verification_code(
            str(verification_request.email),
            code,
            verification_request.purpose,
        )
    except EmailDeliveryError as error:
        challenge.consumed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification is temporarily unavailable",
        ) from error

    return PatientEmailVerificationResult(message=generic_message)


@router.post(
    "/treatments/email-verification/confirm",
    response_model=PatientEmailVerificationResult,
)
@limiter.limit("20/minute")
def confirm_patient_email_verification(
    request: Request,
    confirmation: PatientEmailVerificationConfirm,
    db: Session = Depends(get_db),
):
    """Verify a one-time code and issue a scoped creation grant or session."""
    now = datetime.now(timezone.utc)
    address_hash = _email_hash(str(confirmation.email))
    challenge = db.query(PatientEmailChallenge).filter(
        PatientEmailChallenge.email_hash == address_hash,
        PatientEmailChallenge.purpose == confirmation.purpose,
        PatientEmailChallenge.consumed_at.is_(None),
        PatientEmailChallenge.expires_at > now,
    ).order_by(PatientEmailChallenge.created_at.desc()).with_for_update().first()

    invalid_code = PatientEmailVerificationResult(
        message="Code invalide ou expiré."
    )
    if not challenge or challenge.attempts >= OTP_MAX_ATTEMPTS:
        if challenge:
            challenge.consumed_at = now
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_code.message,
        )

    expected_digest = _digest(
        f"{address_hash}:{confirmation.code}",
        "patient-email-otp",
    )
    if not hmac.compare_digest(challenge.code_digest, expected_digest):
        challenge.attempts += 1
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_code.message,
        )

    challenge.consumed_at = now
    if confirmation.purpose == "registration":
        verification_token = secrets.token_urlsafe(32)
        db.add(PatientEmailGrant(
            email_hash=address_hash,
            token_digest=_digest(verification_token, "patient-registration-grant"),
            expires_at=now + EMAIL_GRANT_LIFETIME,
        ))
        db.commit()
        return PatientEmailVerificationResult(
            message="Adresse e-mail vérifiée.",
            verification_token=verification_token,
            expires_in_seconds=int(EMAIL_GRANT_LIFETIME.total_seconds()),
        )

    session_token = secrets.token_urlsafe(32)
    db.add(PatientManagementSession(
        email=str(confirmation.email),
        token_digest=_digest(session_token, "patient-management-session"),
        expires_at=now + MANAGEMENT_SESSION_LIFETIME,
    ))
    db.commit()
    return PatientEmailVerificationResult(
        message="Vérification réussie.",
        session_token=session_token,
        expires_in_seconds=int(MANAGEMENT_SESSION_LIFETIME.total_seconds()),
    )


@router.post(
    "/treatments/consent",
    response_model=PatientConsentDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_patient_consent(
    consent_data: PatientConsentDraftCreate,
    db: Session = Depends(get_db),
):
    """Record checkbox consent before the final treatment confirmation."""
    now = datetime.now(timezone.utc)
    _require_email_token(
        db,
        str(consent_data.email),
        consent_data.email_verification_token,
        now,
    )
    if consent_data.consent_text_version != settings.PATIENT_CONSENT_TEXT_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The consent text has changed; please review it again",
        )

    consent_draft_token = secrets.token_urlsafe(32)
    db.add(PatientConsentDraft(
        email_hash=_email_hash(str(consent_data.email)),
        token_digest=_digest(consent_draft_token, "patient-consent-draft"),
        consent_analysis=consent_data.consent_analysis,
        consent_alerts=consent_data.consent_alerts,
        consent_text_version=consent_data.consent_text_version,
        consented_at=now,
        expires_at=now + CONSENT_DRAFT_LIFETIME,
    ))
    db.commit()
    return PatientConsentDraftResponse(
        message="Consentement enregistré en attente de confirmation finale.",
        consent_draft_token=consent_draft_token,
        expires_in_seconds=int(CONSENT_DRAFT_LIFETIME.total_seconds()),
    )


@router.post("/treatments", response_model=PatientTreatmentResponse, status_code=status.HTTP_201_CREATED)
async def create_treatment(
    treatment_data: PatientTreatmentCreate,
    db: Session = Depends(get_db)
):
    """
    Final confirmation of consent creates the anonymous treatment declaration.
    """
    now = datetime.now(timezone.utc)
    email = str(treatment_data.email)
    email_hash = _email_hash(email)
    email_grant = _require_email_token(
        db,
        email,
        treatment_data.email_verification_token,
        now,
    )
    draft_digest = _digest(
        treatment_data.consent_draft_token,
        "patient-consent-draft",
    )
    consent_draft = db.query(PatientConsentDraft).filter(
        PatientConsentDraft.email_hash == email_hash,
        PatientConsentDraft.token_digest == draft_digest,
        PatientConsentDraft.consumed_at.is_(None),
        PatientConsentDraft.expires_at > now,
    ).with_for_update().first()
    if not consent_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent confirmation is invalid or expired",
        )

    treatment_duration_months = treatment_data.treatment_duration
    if treatment_duration_months is not None and not isinstance(treatment_duration_months, int):
        try:
            treatment_duration_months = int(treatment_duration_months)
        except (ValueError, TypeError):
            treatment_duration_months = None

    start_dt = treatment_data.treatment_start_date
    end_dt = treatment_data.treatment_end_date
    is_ongoing = treatment_data.treatment_is_ongoing or False
    if treatment_duration_months is None and start_dt and (end_dt or is_ongoing):
        try:
            latest = end_dt if end_dt else (datetime.now(start_dt.tzinfo) if getattr(start_dt, "tzinfo", None) else datetime.now())
            treatment_duration_months = max(1, (latest.year - start_dt.year) * 12 + (latest.month - start_dt.month) + 1)
        except Exception:
            pass

    treatment = PatientTreatment(
        user_id=None,
        name="",
        age=treatment_data.age,
        sex=treatment_data.sex,
        location=treatment_data.location,
        medication_name=treatment_data.medication_name,
        dosage=treatment_data.dosage,
        frequency=treatment_data.frequency,
        treatment_duration=treatment_duration_months,
        treatment_start_date=start_dt,
        treatment_end_date=end_dt,
        treatment_is_ongoing=is_ongoing,
        monthly_cost=treatment_data.monthly_cost,
        unit_price=treatment_data.unit_price,
        access_ease=treatment_data.access_ease,
        effectiveness=treatment_data.effectiveness,
        side_effects=treatment_data.side_effects or "",
        difficulties=treatment_data.difficulties or "",
        additional_comments=treatment_data.additional_comments or "",
        found_medication=treatment_data.found_medication,
        pharmacies_visited=treatment_data.pharmacies_visited,
        waiting_time=treatment_data.waiting_time,
        stockout_frequency=treatment_data.stockout_frequency,
        wants_alert=True,
        contact_email=email,
        email_verified=True,
        email_verified_at=email_grant.created_at,
        consent_analysis=consent_draft.consent_analysis,
        consent_alerts=consent_draft.consent_alerts,
        consent_text_version=consent_draft.consent_text_version,
        consented_at=consent_draft.consented_at,
        consent_confirmed_at=now,
        morning_pills=treatment_data.morning_pills,
        noon_pills=treatment_data.noon_pills,
        evening_pills=treatment_data.evening_pills,
        education_level=treatment_data.education_level,
        minimum_salary=treatment_data.minimum_salary,
        employment_status=treatment_data.employment_status,
        has_financial_resources=treatment_data.has_financial_resources,
        has_alternative_medication=treatment_data.has_alternative_medication,
        alternative_medication_name=treatment_data.alternative_medication_name,
        knows_restock_delay=treatment_data.knows_restock_delay,
        is_restock_delay_precise=treatment_data.is_restock_delay_precise,
        restock_delay_precise=treatment_data.restock_delay_precise,
        # Logique : 
        # - Si knows_restock_delay=True ET is_restock_delay_precise=False → action_when_delay_unknown
        # - Si knows_restock_delay=False → action_when_delay_unknown
        # - Si knows_restock_delay=True ET is_restock_delay_precise=True → pas besoin de action_when_delay_unknown
        action_when_delay_unknown=(
            treatment_data.action_when_delay_unknown 
            if (treatment_data.knows_restock_delay is False or 
                (treatment_data.knows_restock_delay is True and treatment_data.is_restock_delay_precise is False))
            else None
        ),
    )
    
    db.add(treatment)
    consent_draft.consumed_at = now
    db.commit()
    db.refresh(treatment)
    
    return treatment


@router.get("/treatments/mine", response_model=List[PatientTreatmentResponse])
def get_my_treatments(
    management_session: PatientManagementSession = Depends(_get_management_session),
    db: Session = Depends(get_db),
):
    """List only declarations linked to the email verified for this session."""
    return db.query(PatientTreatment).filter(
        PatientTreatment.contact_email == management_session.email,
    ).order_by(desc(PatientTreatment.created_at)).all()


@router.patch(
    "/treatments/mine/{treatment_id}",
    response_model=PatientTreatmentResponse,
)
def update_my_treatment(
    treatment_id: UUID,
    treatment_data: PatientTreatmentUpdate,
    management_session: PatientManagementSession = Depends(_get_management_session),
    db: Session = Depends(get_db),
):
    """Update an owned treatment without allowing changes to identity or consent."""
    treatment = db.query(PatientTreatment).filter(
        PatientTreatment.id == treatment_id,
        PatientTreatment.contact_email == management_session.email,
    ).with_for_update().first()
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment unavailable",
        )

    update_data = treatment_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one editable field is required",
        )
    for field, value in update_data.items():
        setattr(treatment, field, value)
    db.commit()
    db.refresh(treatment)
    return treatment


@router.delete("/treatments/mine")
def delete_my_treatments(
    deletion: PatientDeleteTreatments,
    management_session: PatientManagementSession = Depends(_get_management_session),
    db: Session = Depends(get_db),
):
    """Delete selected declarations atomically for the verified email."""
    deleted_count = _delete_treatments_for_session(
        db,
        management_session,
        deletion.treatment_ids,
    )
    return {"message": "Déclarations supprimées.", "deleted_count": deleted_count}


@router.post("/treatments/mine/consent/withdraw")
def withdraw_my_treatment_consent(
    withdrawal: PatientConsentWithdrawal,
    management_session: PatientManagementSession = Depends(_get_management_session),
    db: Session = Depends(get_db),
):
    """Explicitly withdraw consent, stopping alerts and deleting selected records."""
    deleted_count = _delete_treatments_for_session(
        db,
        management_session,
        withdrawal.treatment_ids,
    )
    return {
        "message": "Consentement retiré; alertes arrêtées et déclarations supprimées.",
        "deleted_count": deleted_count,
    }


@router.post("/treatments/mine/session/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_management_session(
    management_session: PatientManagementSession = Depends(_get_management_session),
    db: Session = Depends(get_db),
):
    db.delete(management_session)
    db.commit()


@router.get("/treatments", response_model=List[PatientTreatmentResponse])
async def get_treatments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère les traitements - ADMIN UNIQUEMENT
    
    Design d'anonymat:
    - POST /treatments: Anonyme vis-à-vis des comptes, après vérification de l'e-mail
    - GET /treatments: ADMIN SEULEMENT (protection anonymat)
    - Seul l'administrateur général peut consulter les traitements
    """
    treatments = db.query(PatientTreatment).order_by(
        desc(PatientTreatment.created_at)
    ).offset(skip).limit(limit).all()
    return treatments


@router.get("/treatments/stats", response_model=TreatmentStats)
async def get_treatment_stats(
    _: None = Depends(require_medecin),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques sur les traitements (médecin/admin uniquement)"""
    total = db.query(func.count(PatientTreatment.id)).filter(
        PatientTreatment.consent_analysis.is_(True),
    ).scalar() or 0
    
    # Calculer l'efficacité moyenne (si le champ existe dans les notes ou autre)
    # Pour l'instant, on retourne des stats de base
    
    stats = TreatmentStats(
        total_treatments=total,
        average_effectiveness=None,
        common_medications=[],
        access_issues=[],
        location_distribution=[],
    )
    
    return stats


@router.get("/treatments/{treatment_id}", response_model=PatientTreatmentResponse)
async def get_treatment(
    treatment_id: UUID,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Récupère un traitement par son ID - ADMIN SEULEMENT"""
    treatment = db.query(PatientTreatment).filter(PatientTreatment.id == treatment_id).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    return treatment


@router.put("/treatments/{treatment_id}", response_model=PatientTreatmentResponse)
async def update_treatment(
    treatment_id: UUID,
    treatment_data: PatientTreatmentUpdate,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Met à jour un traitement - ADMIN SEULEMENT"""
    treatment = db.query(PatientTreatment).filter(PatientTreatment.id == treatment_id).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    update_data = treatment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(treatment, field):
            setattr(treatment, field, value)
    
    db.commit()
    db.refresh(treatment)
    
    return treatment


@router.delete("/treatments/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment(
    treatment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un traitement (l'utilisateur peut supprimer ses propres traitements)"""
    treatment = db.query(PatientTreatment).filter(PatientTreatment.id == treatment_id).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    # Vérifier que l'utilisateur est admin ou propriétaire du traitement
    if current_user.profile is None or current_user.profile.role != "admin":
        if treatment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own treatments"
            )
    
    db.delete(treatment)
    db.commit()
    
    return None
