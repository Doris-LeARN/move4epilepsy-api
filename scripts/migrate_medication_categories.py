"""Add medication domains and therapeutic categories to the database."""

from sqlalchemy import text

import app.models
from app.database.base import Base, engine
from app.models.medication import MedicationCategory, MedicationDomain
from app.models.patient import UnlistedMedicationSubmission


DOMAINS = (
    ("epilepsy", "Épilepsie"),
    ("mental_health", "Santé mentale"),
)

CATEGORIES = (
    ("antiepileptiques", "epilepsy", "Antiépileptiques"),
    ("antidepresseurs", "mental_health", "Antidépresseurs"),
    ("anxiolytiques", "mental_health", "Anxiolytiques"),
    ("antipsychotiques", "mental_health", "Antipsychotiques (neuroleptiques)"),
)


def migrate_medication_categories() -> None:
    with engine.begin() as connection:
        Base.metadata.create_all(
            bind=connection,
            tables=[
                MedicationDomain.__table__,
                MedicationCategory.__table__,
                UnlistedMedicationSubmission.__table__,
            ],
        )

        connection.execute(text(
            "ALTER TABLE medications ADD COLUMN IF NOT EXISTS "
            "category_id VARCHAR REFERENCES medication_categories(id) ON DELETE SET NULL"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_medications_category_id "
            "ON medications (category_id)"
        ))
        connection.execute(text(
            "ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS "
            "medication_category_id VARCHAR REFERENCES medication_categories(id) ON DELETE SET NULL"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_patient_treatments_medication_category_id "
            "ON patient_treatments (medication_category_id)"
        ))

        for domain_id, label in DOMAINS:
            connection.execute(
                text(
                    "INSERT INTO medication_domains (id, label, active) "
                    "VALUES (:id, :label, TRUE) ON CONFLICT (id) DO NOTHING"
                ),
                {"id": domain_id, "label": label},
            )

        for category_id, domain_id, label in CATEGORIES:
            connection.execute(
                text(
                    "INSERT INTO medication_categories "
                    "(id, domain_id, label, active) "
                    "VALUES (:id, :domain_id, :label, TRUE) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": category_id,
                    "domain_id": domain_id,
                    "label": label,
                },
            )

    print("Medication domains and categories are ready.")


if __name__ == "__main__":
    migrate_medication_categories()
