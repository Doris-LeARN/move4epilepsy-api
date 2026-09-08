"""
Endpoints pour les patients et traitements
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.patient import PatientTreatment
from app.schemas.patient import PatientTreatmentCreate, PatientTreatmentResponse, TreatmentStats
from app.core.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.core.permissions import require_medecin, require_admin
from sqlalchemy import func, desc

router = APIRouter()


@router.post("/treatments", response_model=PatientTreatmentResponse, status_code=status.HTTP_201_CREATED)
async def create_treatment(
    treatment_data: PatientTreatmentCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Crée un traitement patient - Correspond à Supabase
    Peut être anonyme (si current_user est None)
    """
    from datetime import datetime

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
        user_id=current_user.id if current_user else None,
        name=treatment_data.name or "",
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
        wants_alert=treatment_data.wants_alert or False,
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
    db.commit()
    db.refresh(treatment)
    
    return treatment


@router.get("/treatments", response_model=List[PatientTreatmentResponse])
async def get_treatments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    medication_name: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Récupère les traitements - ADMIN UNIQUEMENT
    
    Design d'anonymat:
    - POST /treatments: Anonyme (n'importe qui)
    - GET /treatments: ADMIN SEULEMENT (protection anonymat)
    - Seul l'administrateur général peut consulter les traitements
    """
    query = db.query(PatientTreatment)
    
    if medication_name:
        query = query.filter(PatientTreatment.medication_name.ilike(f"%{medication_name}%"))
    
    if location:
        query = query.filter(PatientTreatment.location.ilike(f"%{location}%"))
    
    treatments = query.order_by(desc(PatientTreatment.created_at)).offset(skip).limit(limit).all()
    return treatments


@router.get("/treatments/stats", response_model=TreatmentStats)
async def get_treatment_stats(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_medecin),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques sur les traitements (médecin/admin uniquement)"""
    total = db.query(func.count(PatientTreatment.id)).scalar() or 0
    
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
    current_user: User = Depends(get_current_user),
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
    treatment_data: PatientTreatmentCreate,
    current_user: User = Depends(get_current_user),
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

