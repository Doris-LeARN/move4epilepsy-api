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
    # Créer le traitement avec treatment_duration en mois et treatment_periods en datetime
    from datetime import datetime
    
    # Vérifier que treatment_duration est bien un nombre (mois)
    treatment_duration_months = treatment_data.treatment_duration
    if treatment_duration_months is not None:
        if not isinstance(treatment_duration_months, int):
            try:
                treatment_duration_months = int(treatment_duration_months)
            except (ValueError, TypeError):
                print(f"⚠️ WARNING: treatment_duration n'est pas un nombre: {treatment_duration_months}")
                treatment_duration_months = None
    
    # Traiter treatment_periods (liste avec dates datetime ISO)
    treatment_periods_json = None
    if treatment_data.treatment_periods:
        if isinstance(treatment_data.treatment_periods, list):
            # Format attendu: liste avec start_date, end_date en datetime ISO
            treatment_periods_json = treatment_data.treatment_periods
            print(f"✅ Format traitement_periods: {len(treatment_periods_json)} périodes avec dates datetime")
            if treatment_periods_json and len(treatment_periods_json) > 0:
                first_period = treatment_periods_json[0]
                print(f"  - Première période: start_date={first_period.get('start_date')}, end_date={first_period.get('end_date')}")
        elif isinstance(treatment_data.treatment_periods, dict) and 'periods' in treatment_data.treatment_periods:
            # Ancien format avec periods/metadata - extraire juste les périodes
            treatment_periods_json = treatment_data.treatment_periods.get('periods', [])
            print(f"⚠️ Ancien format détecté, extraction des périodes: {len(treatment_periods_json)} périodes")
        else:
            # Format inconnu, utiliser tel quel
            treatment_periods_json = treatment_data.treatment_periods
    
    # Si treatment_duration est vide/null mais qu'on a des périodes, le calculer depuis les périodes
    if treatment_duration_months is None and treatment_periods_json and len(treatment_periods_json) > 0:
        # Calculer la durée totale en mois depuis les dates
        try:
            earliest_start = None
            latest_end = None
            
            for period in treatment_periods_json:
                start_date_str = period.get('start_date') or period.get('startDateISO')
                end_date_str = period.get('end_date') or period.get('endDateISO')
                
                if start_date_str:
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    if not earliest_start or start_date < earliest_start:
                        earliest_start = start_date
                
                if end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    if not latest_end or end_date > latest_end:
                        latest_end = end_date
                elif period.get('is_ongoing') or period.get('isOngoing'):
                    # Traitement en cours, utiliser maintenant
                    latest_end = datetime.now()
            
            if earliest_start and latest_end:
                years_diff = latest_end.year - earliest_start.year
                months_diff = latest_end.month - earliest_start.month
                treatment_duration_months = years_diff * 12 + months_diff + 1  # +1 pour inclure le mois de début et de fin
                print(f"✅ treatment_duration calculé depuis les périodes: {treatment_duration_months} mois")
        except Exception as e:
            print(f"⚠️ Erreur lors du calcul de treatment_duration: {e}")
    
    # Logs de débogage pour vérifier les valeurs calculées
    print(f"📊 Données reçues pour traitement:")
    print(f"  - treatment_duration: {treatment_duration_months} mois (type: {type(treatment_duration_months).__name__})")
    print(f"  - treatment_periods: {type(treatment_periods_json).__name__}")
    if treatment_periods_json and isinstance(treatment_periods_json, list):
        print(f"    - {len(treatment_periods_json)} périodes")
        if treatment_periods_json:
            first_period = treatment_periods_json[0]
            print(f"    - Première période:")
            print(f"      - start_date: {first_period.get('start_date')}")
            print(f"      - end_date: {first_period.get('end_date')}")
    
    treatment = PatientTreatment(
        name=treatment_data.name or "",
        age=treatment_data.age,
        sex=treatment_data.sex,
        location=treatment_data.location,
        medication_name=treatment_data.medication_name,
        dosage=treatment_data.dosage,
        frequency=treatment_data.frequency,
        treatment_duration=treatment_duration_months,  # Nombre de mois (entier)
        treatment_periods=treatment_periods_json,        # JSONB avec dates datetime ISO
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Récupère les traitements - Correspond à Supabase
    - Médecin/Admin : voit tous les traitements
    - Autres : accès restreint selon RLS Supabase
    """
    query = db.query(PatientTreatment)
    
    # Vérifier les permissions
    user_role = None
    if current_user and current_user.profile:
        user_role = current_user.profile.role
    
    # Dans Supabase, seuls les admins/médecins peuvent lire (selon RLS)
    # Pour l'instant, on permet la lecture à tous les authentifiés
    # TODO: Implémenter la logique RLS exacte
    
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Récupère un traitement par son ID - Correspond à Supabase"""
    treatment = db.query(PatientTreatment).filter(PatientTreatment.id == treatment_id).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    # Dans Supabase, seuls les admins/médecins peuvent lire (selon RLS)
    # Pour l'instant, on permet la lecture à tous les authentifiés
    # TODO: Implémenter la logique RLS exacte
    
    return treatment


@router.put("/treatments/{treatment_id}", response_model=PatientTreatmentResponse)
async def update_treatment(
    treatment_id: UUID,
    treatment_data: PatientTreatmentCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Met à jour un traitement - Correspond à Supabase"""
    treatment = db.query(PatientTreatment).filter(PatientTreatment.id == treatment_id).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    # Dans Supabase, seuls les admins peuvent modifier (selon RLS)
    # Pour l'instant, on permet la modification à tous les authentifiés
    # TODO: Implémenter la logique RLS exacte
    
    # Mettre à jour
    import json
    update_data = treatment_data.model_dump(exclude_unset=True)
    
    # Traiter treatment_periods pour JSONB
    if "treatment_periods" in update_data and update_data["treatment_periods"]:
        update_data["treatment_periods"] = update_data["treatment_periods"]
    
    for field, value in update_data.items():
        if hasattr(treatment, field):
            setattr(treatment, field, value)
    
    db.commit()
    db.refresh(treatment)
    
    return treatment
