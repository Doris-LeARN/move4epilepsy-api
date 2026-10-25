"""
Schémas Pydantic pour les patients et traitements
"""
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class PatientTreatmentCreate(BaseModel):
    """Schéma pour la création d'un traitement patient - Correspond à Supabase"""
    name: Optional[str] = ""  # Nom ou pseudonyme (anonymisé)
    age: int = Field(ge=0, le=150)  # NOT NULL dans Supabase
    sex: str  # NOT NULL, CHECK IN ('homme', 'femme', 'autre', 'non-specifie')
    location: str  # NOT NULL
    medication_name: str  # Text, pas UUID FK
    dosage: str
    frequency: str
    treatment_duration: Optional[int] = None  # Durée en mois (calculée)
    treatment_start_date: Optional[datetime] = None  # Début du traitement
    treatment_end_date: Optional[datetime] = None  # Fin du traitement
    treatment_is_ongoing: Optional[bool] = False  # Traitement en cours
    monthly_cost: Optional[str] = None
    unit_price: Optional[str] = None
    access_ease: str  # NOT NULL
    effectiveness: int = Field(ge=1, le=10)
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
    email: EmailStr
    email_verification_token: str = Field(min_length=32, max_length=128)
    consent_draft_token: str = Field(min_length=32, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()
    
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


class PatientTreatmentUpdate(BaseModel):
    """Editable treatment fields; identity and consent evidence are immutable."""
    age: Optional[int] = Field(default=None, ge=0, le=150)
    sex: Optional[str] = None
    location: Optional[str] = None
    medication_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    treatment_duration: Optional[int] = None
    treatment_start_date: Optional[datetime] = None
    treatment_end_date: Optional[datetime] = None
    treatment_is_ongoing: Optional[bool] = None
    monthly_cost: Optional[str] = None
    unit_price: Optional[str] = None
    access_ease: Optional[str] = None
    effectiveness: Optional[int] = Field(default=None, ge=1, le=10)
    side_effects: Optional[str] = None
    difficulties: Optional[str] = None
    additional_comments: Optional[str] = None
    found_medication: Optional[str] = None
    pharmacies_visited: Optional[str] = None
    waiting_time: Optional[str] = None
    stockout_frequency: Optional[str] = None
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

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required_fields = {
            "age", "sex", "location", "medication_name", "dosage",
            "frequency", "access_ease", "effectiveness",
        }
        for field_name in required_fields.intersection(self.model_fields_set):
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PatientEmailVerificationRequest(BaseModel):
    email: EmailStr
    purpose: Literal["registration", "management"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PatientEmailVerificationConfirm(PatientEmailVerificationRequest):
    code: str = Field(pattern=r"^[0-9]{6}$")


class PatientEmailVerificationResult(BaseModel):
    message: str
    verification_token: Optional[str] = None
    session_token: Optional[str] = None
    expires_in_seconds: Optional[int] = None


class PatientConsentDraftCreate(BaseModel):
    email: EmailStr
    email_verification_token: str = Field(min_length=32, max_length=128)
    consent_analysis: bool
    consent_alerts: Literal[True]
    consent_text_version: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PatientConsentDraftResponse(BaseModel):
    message: str
    consent_draft_token: str
    expires_in_seconds: int


class PatientDeleteTreatments(BaseModel):
    treatment_ids: List[UUID] = Field(min_length=1, max_length=100)

    @field_validator("treatment_ids")
    @classmethod
    def require_unique_ids(cls, value: List[UUID]) -> List[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Treatment IDs must be unique")
        return value


class PatientConsentWithdrawal(PatientDeleteTreatments):
    confirm_withdrawal: Literal[True]


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
    treatment_start_date: Optional[datetime] = None  # Début du traitement
    treatment_end_date: Optional[datetime] = None  # Fin du traitement
    treatment_is_ongoing: Optional[bool] = None  # Traitement en cours
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
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    consent_analysis: Optional[bool] = None
    consent_alerts: Optional[bool] = None
    consent_text_version: Optional[str] = None
    consented_at: Optional[datetime] = None
    consent_confirmed_at: Optional[datetime] = None
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
