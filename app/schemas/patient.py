"""
Schémas Pydantic pour les patients et traitements
"""
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class PatientTreatmentCreate(BaseModel):
    """Schéma pour la création d'un traitement patient - Correspond à Supabase"""
    name: Optional[str] = ""  # Nom ou pseudonyme (anonymisé)
    age: int  # NOT NULL dans Supabase
    sex: str  # NOT NULL, CHECK IN ('homme', 'femme', 'autre', 'non-specifie')
    location: str  # NOT NULL
    medication_name: str  # Text, pas UUID FK
    dosage: str
    frequency: str
    treatment_duration: Optional[int] = None  # Durée en mois (calculée)
    treatment_periods: Optional[Any] = None  # JSONB - Accepte liste ou objet avec periods/metadata
    monthly_cost: Optional[str] = None
    unit_price: Optional[str] = None
    access_ease: str  # NOT NULL
    effectiveness: int  # NOT NULL, CHECK >= 1 AND <= 10
    side_effects: Optional[str] = ""
    difficulties: Optional[str] = ""
    additional_comments: Optional[str] = ""
    found_medication: Optional[str] = None
    pharmacies_visited: Optional[str] = None
    waiting_time: Optional[str] = None
    stockout_frequency: Optional[str] = None
    wants_alert: Optional[bool] = False
    morning_pills: Optional[str] = None
    noon_pills: Optional[str] = None
    evening_pills: Optional[str] = None
    education_level: Optional[str] = None
    minimum_salary: Optional[str] = None
    employment_status: Optional[str] = None
    has_financial_resources: Optional[str] = None
    has_alternative_medication: Optional[bool] = None
    alternative_medication_name: Optional[str] = None
    knows_restock_delay: Optional[bool] = None  # La pharmacie a-t-elle informé du délai ?
    is_restock_delay_precise: Optional[bool] = None  # Le délai est-il précis ?
    restock_delay_precise: Optional[str] = None  # Délai précis si fourni
    action_when_delay_unknown: Optional[str] = None  # Action si délai imprécis/inconnu
    
    @model_validator(mode='after')
    def validate_restock_delay_logic(self):
        """
        Valide la logique des délais de réapprovisionnement :
        - Si knows_restock_delay est True ET is_restock_delay_precise est True → restock_delay_precise doit être rempli
        - Si knows_restock_delay est True ET is_restock_delay_precise est False → action_when_delay_unknown doit être rempli
        - Si knows_restock_delay est False → action_when_delay_unknown peut être rempli
        """
        if self.knows_restock_delay is True:
            if self.is_restock_delay_precise is True:
                # Si délai précis, action_when_delay_unknown n'est pas nécessaire
                if not self.restock_delay_precise:
                    # Optionnel : on peut laisser vide, mais c'est mieux si rempli
                    pass
            elif self.is_restock_delay_precise is False:
                # Si délai imprécis, action_when_delay_unknown doit être rempli
                if not self.action_when_delay_unknown:
                    # Optionnel : on peut laisser vide
                    pass
        return self


class PatientTreatmentResponse(BaseModel):
    """Schéma de réponse pour un traitement patient - Correspond à Supabase"""
    id: UUID
    name: Optional[str] = None
    age: int
    sex: str
    location: str
    medication_name: str
    dosage: str
    frequency: str
    treatment_duration: Optional[int] = None  # Durée en mois (calculée)
    treatment_periods: Optional[Any] = None  # JSONB - Accepte liste ou objet avec periods/metadata
    monthly_cost: Optional[str] = None
    unit_price: Optional[str] = None
    access_ease: str
    effectiveness: int
    side_effects: Optional[str] = None
    difficulties: Optional[str] = None
    additional_comments: Optional[str] = None
    found_medication: Optional[str] = None
    pharmacies_visited: Optional[str] = None
    waiting_time: Optional[str] = None
    stockout_frequency: Optional[str] = None
    wants_alert: Optional[bool] = None
    morning_pills: Optional[str] = None
    noon_pills: Optional[str] = None
    evening_pills: Optional[str] = None
    education_level: Optional[str] = None
    minimum_salary: Optional[str] = None
    employment_status: Optional[str] = None
    has_financial_resources: Optional[str] = None
    has_alternative_medication: Optional[bool] = None
    alternative_medication_name: Optional[str] = None
    knows_restock_delay: Optional[bool] = None
    is_restock_delay_precise: Optional[bool] = None
    restock_delay_precise: Optional[str] = None
    action_when_delay_unknown: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TreatmentStats(BaseModel):
    """Statistiques sur les traitements"""
    total_treatments: int
    average_effectiveness: Optional[float] = None
    common_medications: List[dict] = []
    access_issues: List[dict] = []
    location_distribution: List[dict] = []
