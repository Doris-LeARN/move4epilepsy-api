"""
Modèles Patient
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class PatientSearch(Base):
    """Modèle recherche patient"""
    __tablename__ = "patient_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    department = Column(String, nullable=False)
    commune = Column(String, nullable=True)
    arrondissement = Column(String, nullable=True)
    quartier = Column(String, nullable=True)
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    found_results = Column(Integer, default=0, nullable=False)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relations
    medication = relationship("Medication", back_populates="searches")


class SearchAlert(Base):
    """Modèle alerte de recherche"""
    __tablename__ = "search_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    department = Column(String, nullable=False)
    commune = Column(String, nullable=True)
    arrondissement = Column(String, nullable=True)
    quartier = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    medication = relationship("Medication", back_populates="alerts")


class PatientTreatment(Base):
    """Modèle traitement patient - Correspond exactement à Supabase"""
    __tablename__ = "patient_treatments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    # Champs de base (structure Supabase originale)
    name = Column(String, default="", nullable=True)  # Nom ou pseudonyme (anonymisé)
    age = Column(Integer, nullable=False)  # NOT NULL dans Supabase
    sex = Column(String, nullable=False)  # NOT NULL dans Supabase, CHECK IN ('homme', 'femme', 'autre', 'non-specifie')
    location = Column(String, nullable=False)  # NOT NULL dans Supabase
    medication_name = Column(String, nullable=False, index=True)  # Text, pas FK dans Supabase
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    treatment_duration = Column(Integer, nullable=True)  # Durée en mois (calculée)
    treatment_start_date = Column(DateTime(timezone=True), nullable=True)  # Début du traitement
    treatment_end_date = Column(DateTime(timezone=True), nullable=True)  # Fin du traitement
    treatment_is_ongoing = Column(Boolean, default=False, nullable=True)  # Traitement en cours
    monthly_cost = Column(String, nullable=True)  # Nullable après migration
    unit_price = Column(String, nullable=True)
    access_ease = Column(String, nullable=False)  # NOT NULL dans Supabase originale
    effectiveness = Column(Integer, nullable=False)  # NOT NULL, CHECK >= 1 AND <= 10
    side_effects = Column(Text, default="", nullable=True)
    difficulties = Column(Text, default="", nullable=True)
    additional_comments = Column(Text, default="", nullable=True)
    # Champs ajoutés dans les migrations
    found_medication = Column(String, nullable=True)
    pharmacies_visited = Column(String, nullable=True)
    waiting_time = Column(String, nullable=True)
    stockout_frequency = Column(String, nullable=True)
    wants_alert = Column(Boolean, default=False, nullable=True)
    contact_email = Column(String, nullable=True, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    consent_analysis = Column(Boolean, nullable=True)
    consent_alerts = Column(Boolean, nullable=True)
    consent_text_version = Column(String, nullable=True)
    consented_at = Column(DateTime(timezone=True), nullable=True)
    consent_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    morning_pills = Column(String, nullable=True)
    noon_pills = Column(String, nullable=True)
    evening_pills = Column(String, nullable=True)
    education_level = Column(String, nullable=True)
    minimum_salary = Column(String, nullable=True)
    employment_status = Column(String, nullable=True)
    has_financial_resources = Column(String, nullable=True)
    has_alternative_medication = Column(Boolean, nullable=True)
    alternative_medication_name = Column(String, nullable=True)
    knows_restock_delay = Column(Boolean, nullable=True)  # La pharmacie a-t-elle informé du délai ?
    is_restock_delay_precise = Column(Boolean, nullable=True)  # Le délai est-il précis ?
    restock_delay_precise = Column(String, nullable=True)  # Délai précis si fourni (ex: "2-3 jours")
    action_when_delay_unknown = Column(String, nullable=True)  # Action si délai imprécis/inconnu
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientEmailChallenge(Base):
    """Short-lived, one-time email verification codes."""
    __tablename__ = "patient_email_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email_hash = Column(String, nullable=False, index=True)
    purpose = Column(String, nullable=False, index=True)
    code_digest = Column(String, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientEmailGrant(Base):
    """Short-lived authorization to create consented treatments."""
    __tablename__ = "patient_email_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email_hash = Column(String, nullable=False, index=True)
    token_digest = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientManagementSession(Base):
    """Temporary session restricted to treatments belonging to one email."""
    __tablename__ = "patient_management_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, nullable=False, index=True)
    token_digest = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientConsentDraft(Base):
    """Short-lived record of checkbox consent pending final confirmation."""
    __tablename__ = "patient_consent_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email_hash = Column(String, nullable=False, index=True)
    token_digest = Column(String, unique=True, nullable=False, index=True)
    consent_analysis = Column(Boolean, nullable=False)
    consent_alerts = Column(Boolean, nullable=False)
    consent_text_version = Column(String, nullable=False)
    consented_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientAvailabilityNotification(Base):
    """Outbox entry for one treatment and one stock-restoration event."""
    __tablename__ = "patient_availability_notifications"
    __table_args__ = (
        UniqueConstraint(
            "treatment_id",
            "stock_id",
            "availability_version",
            name="uq_patient_availability_notification_event",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    treatment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patient_treatments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pharmacy_stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    availability_version = Column(Integer, nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
