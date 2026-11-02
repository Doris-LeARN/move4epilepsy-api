"""Add structured treatment-affordability and rights-advocacy analytics fields."""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "move4epilepsy"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

COLUMNS = {
    "cost_related_treatment_change": "VARCHAR(40)",
    "discrimination_context": "VARCHAR(40)",
    "rights_support_need": "VARCHAR(40)",
}


def migrate_patient_advocacy_analytics():
    with psycopg2.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            for column_name, column_type in COLUMNS.items():
                cursor.execute(
                    f"ALTER TABLE patient_treatments "
                    f"ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
                )


if __name__ == "__main__":
    migrate_patient_advocacy_analytics()
