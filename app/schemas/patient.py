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
    age: int = Field(ge=1, le=120)
    sex: Literal["homme", "femme", "autre", "non-specifie"]
    location: str  # NOT NULL
    medication_name: str = Field(min_length=1, max_length=255)  # Text, pas UUID FK
    dosage: str = Field(min_length=1)
    frequency: str = Field(min_length=1)
    treatment_duration: int = Field(ge=1)
    treatment_start_date: datetime
    treatment_end_date: Optional[datetime] = None  # Fin du traitement
    treatment_is_ongoing: bool
    medication_category_id: Optional[str] = None
    medication_is_unlisted: bool = False
    medication_country: Optional[str] = Field(default=None, max_length=100)
    monthly_cost: str = Field(pattern=r"^(?:\d+(?:\.\d{1,2})?|prefer-not-to-say)$")
    unit_price: str = Field(pattern=r"^(?:\d+(?:\.\d{1,2})?|prefer-not-to-say)$")
    access_ease: str = Field(min_length=1)
    effectiveness: int = Field(ge=1, le=10)
    side_effects: Optional[str] = ""
    difficulties: Optional[str] = ""
    additional_comments: Optional[str] = ""
    found_medication: Literal["yes", "no", "partially", "unknown"]
    pharmacies_visited: str = Field(pattern=r"^\d+$")
    waiting_time: Literal["same-day", "1-3-days", "4-7-days", "more-than-7-days", "unknown"]
    stockout_frequency: Literal["never", "monthly", "weekly", "often", "unknown"]
    wants_alert: bool
    morning_pills: str = Field(pattern=r"^\d+$")
    noon_pills: str = Field(pattern=r"^\d+$")
    evening_pills: str = Field(pattern=r"^\d+$")
    education_level: Literal[
        "no-formal-education", "primary", "secondary", "higher", "prefer-not-to-say",
    ]
    minimum_salary: str = Field(pattern=r"^(?:\d+(?:\.\d{1,2})?|prefer-not-to-say)$")
    employment_status: Literal[
        "employed", "self-employed", "unemployed", "student", "retired", "other-response",
        "prefer-not-to-say",
    ]
    has_financial_resources: Literal["yes", "no", "partially", "prefer-not-to-say"]
    emotional_impact: Literal[
        "none", "mild", "moderate", "high", "prefer-not-to-say",
    ]
    social_stigma: Literal[
        "never", "sometimes", "often", "always", "prefer-not-to-say",
    ]
    professional_impact: Literal[
        "none", "mild", "moderate", "major", "not-applicable", "prefer-not-to-say",
    ]
    social_support: Literal[
        "strong", "partial", "limited", "none", "prefer-not-to-say",
    ]
    access_barrier: Literal[
        "none", "cost", "distance", "transport", "stockout", "information", "multiple",
        "other-response", "prefer-not-to-say",
    ]
    cost_related_treatment_change: Literal[
        "none", "delayed_purchase", "missed_or_reduced_doses", "stopped_treatment",
        "prefer-not-to-say",
    ]
    discrimination_context: Literal[
        "none", "healthcare", "work", "education", "family_community", "public_services",
        "multiple_contexts", "prefer-not-to-say",
    ]
    rights_support_need: Literal[
        "none", "rights_information", "report_discrimination", "legal_support",
        "psychological_support", "peer_support", "other-response", "prefer-not-to-say",
    ]
    has_alternative_medication: bool
    alternative_medication_name: Optional[str] = None
    knows_restock_delay: bool
    is_restock_delay_precise: Optional[bool] = None  # Not applicable when no delay was communicated
    restock_delay_precise: Optional[str] = None  # Délai précis si fourni
    action_when_delay_unknown: Optional[str] = None  # Action si délai imprécis/inconnu
    email: EmailStr
    email_verification_token: str = Field(min_length=32, max_length=128)
    consent_draft_token: str = Field(min_length=32, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("medication_name")
    @classmethod
    def normalize_medication_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("medication_country")
    @classmethod
    def normalize_medication_country(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else None
    
    @model_validator(mode='after')
    def validate_restock_delay_logic(self):
        if self.knows_restock_delay and self.is_restock_delay_precise is None:
            raise ValueError("A precision response is required when a restock delay is known")
        if not self.knows_restock_delay and self.is_restock_delay_precise is not None:
            raise ValueError("Restock delay precision is not applicable when no delay is known")
        if self.is_restock_delay_precise and not (self.restock_delay_precise or "").strip():
            raise ValueError("A precise restock delay must be provided")
        if (not self.knows_restock_delay or self.is_restock_delay_precise is False) and not (
            self.action_when_delay_unknown or ""
        ).strip():
            raise ValueError("An action is required when the restock delay is unknown or unclear")
        if self.is_restock_delay_precise and self.action_when_delay_unknown:
            raise ValueError("Unknown-delay action is not applicable for a precise delay")
        if self.treatment_is_ongoing and self.treatment_end_date is not None:
            raise ValueError("An ongoing treatment cannot have an end date")
        if not self.treatment_is_ongoing and self.treatment_end_date is None:
            raise ValueError("An end date is required for a completed treatment")
        if self.has_alternative_medication and not (self.alternative_medication_name or "").strip():
            raise ValueError("An alternative medication name is required when one is reported")
        if not self.has_alternative_medication and self.alternative_medication_name:
            raise ValueError("An alternative medication name requires an alternative to be reported")
        return self

    @model_validator(mode="after")
    def validate_unlisted_medication_details(self):
        if not self.medication_name:
            raise ValueError("Medication name cannot be blank")
        if self.medication_is_unlisted:
            if not self.medication_country:
                raise ValueError("A country is required for an unlisted medication")
        elif self.medication_country:
            raise ValueError("A country can only be provided for an unlisted medication")
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
    medication_category_id: Optional[str] = None
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
    emotional_impact: Optional[Literal[
        "none", "mild", "moderate", "high", "prefer-not-to-say",
    ]] = None
    social_stigma: Optional[Literal[
        "never", "sometimes", "often", "always", "prefer-not-to-say",
    ]] = None
    professional_impact: Optional[Literal[
        "none", "mild", "moderate", "major", "not-applicable", "prefer-not-to-say",
    ]] = None
    social_support: Optional[Literal[
        "strong", "partial", "limited", "none", "prefer-not-to-say",
    ]] = None
    access_barrier: Optional[Literal[
        "none", "cost", "distance", "transport", "stockout", "information", "multiple",
        "other-response", "prefer-not-to-say",
    ]] = None
    cost_related_treatment_change: Optional[Literal[
        "none", "delayed_purchase", "missed_or_reduced_doses", "stopped_treatment",
        "prefer-not-to-say",
    ]] = None
    discrimination_context: Optional[Literal[
        "none", "healthcare", "work", "education", "family_community", "public_services",
        "multiple_contexts", "prefer-not-to-say",
    ]] = None
    rights_support_need: Optional[Literal[
        "none", "rights_information", "report_discrimination", "legal_support",
        "psychological_support", "peer_support", "other-response", "prefer-not-to-say",
    ]] = None
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
    consent_alerts: bool
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


class UnlistedMedicationSubmissionResponse(BaseModel):
    status: Literal[
        "pending_validation",
        "needs_clarification",
        "approved",
        "rejected",
    ]
    country: str
    location: str
    submitted_at: datetime

    class Config:
        from_attributes = True


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
    medication_category_id: Optional[str] = None
    unlisted_medication_submission: Optional["UnlistedMedicationSubmissionResponse"] = None
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
    emotional_impact: Optional[str] = None
    social_stigma: Optional[str] = None
    professional_impact: Optional[str] = None
    social_support: Optional[str] = None
    access_barrier: Optional[str] = None
    cost_related_treatment_change: Optional[str] = None
    discrimination_context: Optional[str] = None
    rights_support_need: Optional[str] = None
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
