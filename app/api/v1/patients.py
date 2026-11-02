"""
Endpoints pour les patients et traitements
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
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
    UnlistedMedicationSubmission,
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
from sqlalchemy import String, case, cast, desc, func, or_
from app.core.config import settings
from app.core.email import EmailDeliveryError, send_patient_verification_code
from app.core.rate_limiter import limiter
from app.models.medication import Medication, MedicationCategory

router = APIRouter()

OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_REQUESTS_PER_HOUR = 5
OTP_MAX_ATTEMPTS = 5
EMAIL_GRANT_LIFETIME = timedelta(minutes=20)
CONSENT_DRAFT_LIFETIME = timedelta(minutes=30)
MANAGEMENT_SESSION_LIFETIME = timedelta(minutes=30)
PUBLIC_ANALYTICS_MIN_GROUP_SIZE = 10


def _validate_medication_category(db: Session, category_id: Optional[str]) -> None:
    if category_id is None:
        return
    category = db.query(MedicationCategory.id).filter(
        MedicationCategory.id == category_id,
        MedicationCategory.active.is_(True),
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medication category not found or inactive",
        )


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
    if treatment_data.wants_alert and not consent_draft.consent_alerts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Availability alerts require explicit alert consent",
        )
    _validate_medication_category(db, treatment_data.medication_category_id)

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
        medication_category_id=treatment_data.medication_category_id,
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
        wants_alert=bool(treatment_data.wants_alert and consent_draft.consent_alerts),
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
        emotional_impact=treatment_data.emotional_impact,
        social_stigma=treatment_data.social_stigma,
        professional_impact=treatment_data.professional_impact,
        social_support=treatment_data.social_support,
        access_barrier=treatment_data.access_barrier,
        cost_related_treatment_change=treatment_data.cost_related_treatment_change,
        discrimination_context=treatment_data.discrimination_context,
        rights_support_need=treatment_data.rights_support_need,
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
    if treatment_data.medication_is_unlisted:
        treatment.unlisted_medication_submission = UnlistedMedicationSubmission(
            medication_name=treatment_data.medication_name.strip(),
            category_id=treatment_data.medication_category_id,
            country=treatment_data.medication_country.strip(),
            location=treatment_data.location.strip(),
            status="pending_validation",
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
    if "medication_category_id" in update_data:
        _validate_medication_category(db, update_data["medication_category_id"])
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


def _public_category_breakdown(db: Session, category_expression):
    rows = db.query(
        category_expression.label("category"),
        func.count(PatientTreatment.id).label("count"),
    ).filter(
        PatientTreatment.consent_analysis.is_(True),
        category_expression.is_not(None),
    ).group_by(category_expression).all()

    visible = []
    suppressed_count = 0
    for category, count in rows:
        if count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
            visible.append({"category": category, "count": count})
        else:
            suppressed_count += count

    if suppressed_count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
        visible.append({"category": "other", "count": suppressed_count})

    return {
        "items": sorted(visible, key=lambda item: item["count"], reverse=True),
        "has_suppressed_groups": suppressed_count > 0,
    }


def _allowed_category(column, categories: List[str]):
    normalized_value = func.lower(func.trim(column))
    return case(
        *[(normalized_value == category, category) for category in categories],
        else_=None,
    )


def _public_numeric_breakdown(
    db: Session,
    column,
    buckets: List[tuple[Optional[Decimal], str]],
    consented,
):
    value_expression = func.trim(cast(column, String))
    rows = db.query(
        value_expression.label("value"),
        func.count(PatientTreatment.id).label("count"),
    ).filter(
        consented,
        column.is_not(None),
        value_expression != "",
    ).group_by(value_expression).all()

    counts = {}
    for raw_value, count in rows:
        try:
            value = Decimal(raw_value)
        except (InvalidOperation, TypeError):
            category = "prefer-not-to-say" if raw_value == "prefer-not-to-say" else "unknown"
        else:
            if not value.is_finite() or value < 0:
                category = "unknown"
            else:
                category = next(
                    (label for upper_bound, label in buckets if upper_bound is None or value <= upper_bound),
                    buckets[-1][1],
                )
        counts[category] = counts.get(category, 0) + count

    visible = []
    suppressed_count = 0
    for category, count in counts.items():
        if count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
            visible.append({"category": category, "count": count})
        else:
            suppressed_count += count
    if suppressed_count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
        visible.append({"category": "other", "count": suppressed_count})

    return {
        "items": sorted(visible, key=lambda item: item["count"], reverse=True),
        "has_suppressed_groups": suppressed_count > 0,
    }


@router.get("/analytics/public")
def get_public_treatment_analytics(db: Session = Depends(get_db)):
    """Return privacy-protected aggregates from declarations consenting to analysis."""
    consented = PatientTreatment.consent_analysis.is_(True)
    raw_sample_size = db.query(func.count(PatientTreatment.id)).filter(consented).scalar() or 0
    if raw_sample_size < PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
        return {
            "sample_size": None,
            "minimum_group_size": PUBLIC_ANALYTICS_MIN_GROUP_SIZE,
            "source": "consented_treatments",
            "data_suppressed": True,
            "breakdowns": {},
            "response_coverage": {},
            "monthly_trend": [],
            "forecast": None,
            "forecast_method": "linear_extrapolation_of_monthly_consenting_declarations",
        }
    sample_size = raw_sample_size

    age_group = case(
        (PatientTreatment.age < 18, "0-17"),
        (PatientTreatment.age < 30, "18-29"),
        (PatientTreatment.age < 45, "30-44"),
        (PatientTreatment.age < 60, "45-59"),
        else_="60+",
    )
    sex_value = func.lower(func.trim(PatientTreatment.sex))
    sex_group = case(
        (sex_value == "homme", "male"),
        (sex_value == "femme", "female"),
        (sex_value == "autre", "other"),
        (sex_value == "non-specifie", "not-specified"),
        else_=None,
    )
    access_value = func.lower(func.trim(PatientTreatment.access_ease))
    access_group = case(
        (access_value == "easy", "easy"),
        (access_value == "difficult", "difficult"),
        (access_value == "very-difficult", "very-difficult"),
        else_=None,
    )
    effectiveness_group = case(
        (PatientTreatment.effectiveness <= 4, "low"),
        (PatientTreatment.effectiveness <= 7, "moderate"),
        else_="high",
    )
    financial_value = func.lower(func.trim(PatientTreatment.has_financial_resources))
    financial_group = case(
        (financial_value == "yes", "yes"),
        (financial_value == "no", "no"),
        (financial_value == "partially", "partially"),
        else_=None,
    )
    education_group = _allowed_category(PatientTreatment.education_level, [
        "no-formal-education", "primary", "secondary", "higher", "prefer-not-to-say",
    ])
    employment_group = _allowed_category(PatientTreatment.employment_status, [
        "employed", "self-employed", "unemployed", "student", "retired", "other-response",
        "prefer-not-to-say",
    ])
    emotional_impact_group = _allowed_category(PatientTreatment.emotional_impact, [
        "none", "mild", "moderate", "high", "prefer-not-to-say",
    ])
    social_stigma_group = _allowed_category(PatientTreatment.social_stigma, [
        "never", "sometimes", "often", "always", "prefer-not-to-say",
    ])
    professional_impact_group = _allowed_category(PatientTreatment.professional_impact, [
        "none", "mild", "moderate", "major", "not-applicable", "prefer-not-to-say",
    ])
    social_support_group = _allowed_category(PatientTreatment.social_support, [
        "strong", "partial", "limited", "none", "prefer-not-to-say",
    ])
    access_barrier_group = _allowed_category(PatientTreatment.access_barrier, [
        "none", "cost", "distance", "transport", "stockout", "information", "multiple",
        "other-response", "prefer-not-to-say",
    ])
    cost_related_treatment_change_group = _allowed_category(
        PatientTreatment.cost_related_treatment_change,
        ["none", "delayed_purchase", "missed_or_reduced_doses", "stopped_treatment", "prefer-not-to-say"],
    )
    discrimination_context_group = _allowed_category(
        PatientTreatment.discrimination_context,
        [
            "none", "healthcare", "work", "education", "family_community", "public_services",
            "multiple_contexts", "prefer-not-to-say",
        ],
    )
    rights_support_need_group = _allowed_category(
        PatientTreatment.rights_support_need,
        [
            "none", "rights_information", "report_discrimination", "legal_support",
            "psychological_support", "peer_support", "other-response", "prefer-not-to-say",
        ],
    )
    found_medication_group = _allowed_category(PatientTreatment.found_medication, [
        "yes", "no", "partially", "unknown",
    ])
    waiting_time_group = _allowed_category(PatientTreatment.waiting_time, [
        "same-day", "1-3-days", "4-7-days", "more-than-7-days", "unknown",
    ])
    stockout_frequency_group = _allowed_category(PatientTreatment.stockout_frequency, [
        "never", "monthly", "weekly", "often", "unknown",
    ])
    alternative_medication_group = case(
        (PatientTreatment.has_alternative_medication.is_(True), "yes"),
        (PatientTreatment.has_alternative_medication.is_(False), "no"),
        else_=None,
    )
    ongoing_group = case(
        (PatientTreatment.treatment_is_ongoing.is_(True), "ongoing"),
        (PatientTreatment.treatment_is_ongoing.is_(False), "ended"),
        else_=None,
    )
    medication_category_group = _allowed_category(PatientTreatment.medication_category_id, [
        "antiepileptiques", "antidepresseurs", "anxiolytiques", "antipsychotiques",
    ])
    wants_alert_group = case(
        (PatientTreatment.wants_alert.is_(True), "yes"),
        (PatientTreatment.wants_alert.is_(False), "no"),
        else_=None,
    )
    restock_delay_group = case(
        (PatientTreatment.knows_restock_delay.is_(True), "yes"),
        (PatientTreatment.knows_restock_delay.is_(False), "no"),
        else_=None,
    )
    precise_restock_delay_group = case(
        (PatientTreatment.is_restock_delay_precise.is_(True), "yes"),
        (PatientTreatment.is_restock_delay_precise.is_(False), "no"),
        else_=None,
    )

    catalog_names = {
        name.strip().casefold(): name.strip()
        for (name,) in db.query(Medication.name).filter(Medication.active.is_(True)).all()
        if name and name.strip()
    }
    medication_rows = db.query(
        func.lower(func.trim(PatientTreatment.medication_name)).label("medication"),
        func.count(PatientTreatment.id).label("count"),
    ).filter(
        consented,
        PatientTreatment.medication_name.is_not(None),
        func.trim(PatientTreatment.medication_name) != "",
    ).group_by(func.lower(func.trim(PatientTreatment.medication_name))).all()

    medication_counts = {}
    unlisted_medication_count = 0
    for medication_name, count in medication_rows:
        catalog_name = catalog_names.get(medication_name.strip().casefold())
        if catalog_name:
            medication_counts[catalog_name] = medication_counts.get(catalog_name, 0) + count
        else:
            unlisted_medication_count += count
    medication_categories = [
        {"category": name, "count": count}
        for name, count in medication_counts.items()
        if count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE
    ]
    suppressed_medication_count = sum(
        count for count in medication_counts.values()
        if count < PUBLIC_ANALYTICS_MIN_GROUP_SIZE
    ) + unlisted_medication_count
    if suppressed_medication_count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE:
        medication_categories.append({
            "category": "other",
            "count": suppressed_medication_count,
        })

    location_aliases = {
        "cotonou": "cotonou",
        "abomey-calavi": "abomey-calavi",
        "abomey": "abomey",
    }
    location_rows = db.query(
        func.lower(func.trim(PatientTreatment.location)).label("location"),
        func.count(PatientTreatment.id).label("count"),
    ).filter(
        consented,
        PatientTreatment.location.is_not(None),
        func.trim(PatientTreatment.location) != "",
    ).group_by(func.lower(func.trim(PatientTreatment.location))).all()
    recognized_locations = [
        (location_aliases[location], count)
        for location, count in location_rows
        if location in location_aliases
    ]
    has_suppressed_locations = any(
        count < PUBLIC_ANALYTICS_MIN_GROUP_SIZE
        for _, count in recognized_locations
    )
    locations = [] if has_suppressed_locations else [
        {"category": location, "count": count}
        for location, count in recognized_locations
    ]

    coverage_fields = {
        "age": PatientTreatment.age,
        "sex": PatientTreatment.sex,
        "location": PatientTreatment.location,
        "medication_name": PatientTreatment.medication_name,
        "medication_category_id": PatientTreatment.medication_category_id,
        "dosage": PatientTreatment.dosage,
        "frequency": PatientTreatment.frequency,
        "treatment_duration": PatientTreatment.treatment_duration,
        "treatment_start_date": PatientTreatment.treatment_start_date,
        "treatment_end_date": PatientTreatment.treatment_end_date,
        "treatment_is_ongoing": PatientTreatment.treatment_is_ongoing,
        "monthly_cost": PatientTreatment.monthly_cost,
        "unit_price": PatientTreatment.unit_price,
        "access_ease": PatientTreatment.access_ease,
        "effectiveness": PatientTreatment.effectiveness,
        "found_medication": PatientTreatment.found_medication,
        "pharmacies_visited": PatientTreatment.pharmacies_visited,
        "waiting_time": PatientTreatment.waiting_time,
        "stockout_frequency": PatientTreatment.stockout_frequency,
        "wants_alert": PatientTreatment.wants_alert,
        "morning_pills": PatientTreatment.morning_pills,
        "noon_pills": PatientTreatment.noon_pills,
        "evening_pills": PatientTreatment.evening_pills,
        "education_level": PatientTreatment.education_level,
        "employment_status": PatientTreatment.employment_status,
        "minimum_salary": PatientTreatment.minimum_salary,
        "has_financial_resources": PatientTreatment.has_financial_resources,
        "emotional_impact": PatientTreatment.emotional_impact,
        "social_stigma": PatientTreatment.social_stigma,
        "professional_impact": PatientTreatment.professional_impact,
        "social_support": PatientTreatment.social_support,
        "access_barrier": PatientTreatment.access_barrier,
        "cost_related_treatment_change": PatientTreatment.cost_related_treatment_change,
        "discrimination_context": PatientTreatment.discrimination_context,
        "rights_support_need": PatientTreatment.rights_support_need,
        "has_alternative_medication": PatientTreatment.has_alternative_medication,
        "alternative_medication_name": PatientTreatment.alternative_medication_name,
        "knows_restock_delay": PatientTreatment.knows_restock_delay,
        "is_restock_delay_precise": PatientTreatment.is_restock_delay_precise,
        "restock_delay_precise": PatientTreatment.restock_delay_precise,
        "action_when_delay_unknown": PatientTreatment.action_when_delay_unknown,
        "side_effects": PatientTreatment.side_effects,
        "difficulties": PatientTreatment.difficulties,
        "additional_comments": PatientTreatment.additional_comments,
    }
    coverage = {}
    for field_name, column in coverage_fields.items():
        answered = db.query(func.count(PatientTreatment.id)).filter(
            consented,
            func.nullif(func.trim(cast(column, String)), "").is_not(None),
        ).scalar() or 0
        not_answered = max(0, sample_size - answered)
        coverage[field_name] = (
            {"answered": answered, "not_answered": not_answered}
            if min(answered, not_answered) >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE
            else {"answered": None, "not_answered": None, "suppressed": True}
        )

    monthly_rows = db.query(
        func.date_trunc("month", PatientTreatment.created_at).label("month"),
        func.count(PatientTreatment.id).label("count"),
    ).filter(
        consented,
    ).group_by(func.date_trunc("month", PatientTreatment.created_at)).order_by(
        desc(func.date_trunc("month", PatientTreatment.created_at)),
    ).limit(12).all()
    monthly_rows.reverse()
    monthly_trend = []
    forecast = None
    if len(monthly_rows) >= 6 and all(
        count >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE for _, count in monthly_rows
    ):
        monthly_trend = [
            {"month": month.strftime("%Y-%m"), "count": count}
            for month, count in monthly_rows
        ]
        values = [count for _, count in monthly_rows]
        mean_x = (len(values) - 1) / 2
        mean_y = sum(values) / len(values)
        denominator = sum((index - mean_x) ** 2 for index in range(len(values)))
        slope = sum(
            (index - mean_x) * (value - mean_y)
            for index, value in enumerate(values)
        ) / denominator
        intercept = mean_y - slope * mean_x
        forecast_candidates = [
            {
                "month_offset": offset,
                "estimated_declarations": max(
                    0,
                    round(intercept + slope * (len(values) - 1 + offset)),
                ),
            }
            for offset in range(1, 4)
        ]
        if all(
            item["estimated_declarations"] >= PUBLIC_ANALYTICS_MIN_GROUP_SIZE
            for item in forecast_candidates
        ):
            forecast = forecast_candidates

    return {
        "sample_size": sample_size,
        "minimum_group_size": PUBLIC_ANALYTICS_MIN_GROUP_SIZE,
        "source": "consented_treatments",
        "breakdowns": {
            "age": _public_category_breakdown(db, age_group),
            "sex": _public_category_breakdown(db, sex_group),
            "access_ease": _public_category_breakdown(db, access_group),
            "effectiveness": _public_category_breakdown(db, effectiveness_group),
            "financial_resources": _public_category_breakdown(db, financial_group),
            "education": _public_category_breakdown(db, education_group),
            "employment": _public_category_breakdown(db, employment_group),
            "emotional_impact": _public_category_breakdown(db, emotional_impact_group),
            "social_stigma": _public_category_breakdown(db, social_stigma_group),
            "professional_impact": _public_category_breakdown(db, professional_impact_group),
            "social_support": _public_category_breakdown(db, social_support_group),
            "access_barriers": _public_category_breakdown(db, access_barrier_group),
            "cost_related_treatment_change": _public_category_breakdown(
                db, cost_related_treatment_change_group,
            ),
            "discrimination_context": _public_category_breakdown(
                db, discrimination_context_group,
            ),
            "rights_support_need": _public_category_breakdown(db, rights_support_need_group),
            "found_medication": _public_category_breakdown(db, found_medication_group),
            "waiting_time": _public_category_breakdown(db, waiting_time_group),
            "stockout_frequency": _public_category_breakdown(db, stockout_frequency_group),
            "alternative_medication": _public_category_breakdown(db, alternative_medication_group),
            "treatment_status": _public_category_breakdown(db, ongoing_group),
            "medications": {
                "items": sorted(
                    medication_categories,
                    key=lambda item: item["count"],
                    reverse=True,
                ),
                "has_suppressed_groups": suppressed_medication_count > 0,
            },
            "medication_category": _public_category_breakdown(db, medication_category_group),
            "treatment_duration": _public_numeric_breakdown(
                db,
                PatientTreatment.treatment_duration,
                [(Decimal(3), "1-3"), (Decimal(12), "4-12"), (Decimal(60), "13-60"), (None, "61+")],
                consented,
            ),
            "pharmacies_visited": _public_numeric_breakdown(
                db,
                PatientTreatment.pharmacies_visited,
                [(Decimal(0), "0"), (Decimal(2), "1-2"), (Decimal(5), "3-5"), (None, "6+")],
                consented,
            ),
            "morning_pills": _public_numeric_breakdown(
                db,
                PatientTreatment.morning_pills,
                [(Decimal(0), "0"), (Decimal(1), "1"), (Decimal(2), "2"), (None, "3+")],
                consented,
            ),
            "noon_pills": _public_numeric_breakdown(
                db,
                PatientTreatment.noon_pills,
                [(Decimal(0), "0"), (Decimal(1), "1"), (Decimal(2), "2"), (None, "3+")],
                consented,
            ),
            "evening_pills": _public_numeric_breakdown(
                db,
                PatientTreatment.evening_pills,
                [(Decimal(0), "0"), (Decimal(1), "1"), (Decimal(2), "2"), (None, "3+")],
                consented,
            ),
            "wants_alert": _public_category_breakdown(db, wants_alert_group),
            "knows_restock_delay": _public_category_breakdown(db, restock_delay_group),
            "restock_delay_precision": _public_category_breakdown(db, precise_restock_delay_group),
            "locations": {
                "items": sorted(locations, key=lambda item: item["count"], reverse=True),
                "has_suppressed_groups": has_suppressed_locations,
            },
        },
        "response_coverage": coverage,
        "monthly_trend": monthly_trend,
        "forecast": forecast,
        "forecast_method": "linear_extrapolation_of_monthly_consenting_declarations",
    }


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
