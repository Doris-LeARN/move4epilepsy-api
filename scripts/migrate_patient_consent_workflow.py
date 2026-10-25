"""Add verified-email, consent-proof, and temporary-session persistence."""

from sqlalchemy import text

from app.database.base import Base, engine
from app.models.patient import (
    PatientConsentDraft,
    PatientEmailChallenge,
    PatientEmailGrant,
    PatientManagementSession,
    PatientAvailabilityNotification,
)


def migrate_patient_consent_workflow() -> None:
    with engine.begin() as connection:
        for statement in (
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS contact_email VARCHAR",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS consent_analysis BOOLEAN",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS consent_alerts BOOLEAN",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS consent_text_version VARCHAR",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS consented_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS consent_confirmed_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE pharmacy_stocks ADD COLUMN IF NOT EXISTS availability_version INTEGER NOT NULL DEFAULT 0",
            "CREATE INDEX IF NOT EXISTS ix_patient_treatments_contact_email ON patient_treatments (contact_email)",
        ):
            connection.execute(text(statement))

        Base.metadata.create_all(
            bind=connection,
            tables=[
                PatientEmailChallenge.__table__,
                PatientEmailGrant.__table__,
                PatientManagementSession.__table__,
                PatientConsentDraft.__table__,
                PatientAvailabilityNotification.__table__,
            ],
        )

    print("Patient consent workflow schema is ready.")


if __name__ == "__main__":
    migrate_patient_consent_workflow()
