"""
Migration: Remplacer la colonne treatment_periods (JSONB) par 3 colonnes :
- treatment_start_date (début du traitement)
- treatment_end_date (fin du traitement)
- treatment_is_ongoing (traitement en cours)

Exécuter depuis la racine du projet : python scripts/migrate_treatment_periods_to_columns.py
"""

import os
import json
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "move4epilepsy"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def parse_date(s):
    """Parse une chaîne datetime ISO en date pour comparaison."""
    if not s:
        return None
    try:
        from datetime import datetime
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def extract_from_periods(periods_json):
    """
    À partir d'un JSONB treatment_periods (liste de périodes), retourne
    (start_date, end_date, is_ongoing) pour la migration.
    """
    if not periods_json:
        return None, None, False
    try:
        if isinstance(periods_json, str):
            periods = json.loads(periods_json)
        else:
            periods = periods_json
        if isinstance(periods, dict) and "periods" in periods:
            periods = periods["periods"]
        if not isinstance(periods, list) or len(periods) == 0:
            return None, None, False
    except Exception:
        return None, None, False

    earliest = None
    latest = None
    is_ongoing = False
    for p in periods:
        if not isinstance(p, dict):
            continue
        start_str = p.get("start_date") or p.get("startDateISO") or (p.get("startDate") and f"{p['startDate']}T00:00:00")
        end_str = p.get("end_date") or p.get("endDateISO") or (p.get("endDate") and f"{p['endDate']}T23:59:59")
        if p.get("is_ongoing") or p.get("isOngoing"):
            is_ongoing = True
        start_dt = parse_date(start_str)
        end_dt = parse_date(end_str)
        if start_dt and (not earliest or start_dt < earliest):
            earliest = start_dt
        if end_dt and (not latest or end_dt > latest):
            latest = end_dt
        if is_ongoing and not latest:
            from datetime import datetime
            latest = datetime.now(earliest.tzinfo if earliest and getattr(earliest, "tzinfo", None) else None)

    return earliest, latest, is_ongoing


def run_migration():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("🔄 Migration: treatment_periods → treatment_start_date, treatment_end_date, treatment_is_ongoing")

        # 1. Ajouter les 3 colonnes
        print("\n1️⃣ Ajout des colonnes treatment_start_date, treatment_end_date, treatment_is_ongoing...")
        for col, typ in [
            ("treatment_start_date", "TIMESTAMP WITH TIME ZONE"),
            ("treatment_end_date", "TIMESTAMP WITH TIME ZONE"),
            ("treatment_is_ongoing", "BOOLEAN DEFAULT FALSE"),
        ]:
            cur.execute(
                f"ALTER TABLE patient_treatments ADD COLUMN IF NOT EXISTS {col} {typ};"
            )
        conn.commit()
        print("✅ Colonnes ajoutées")

        # 2. Migrer les données depuis treatment_periods
        print("\n2️⃣ Migration des données depuis treatment_periods...")
        cur.execute("SELECT id, treatment_periods FROM patient_treatments WHERE treatment_periods IS NOT NULL;")
        rows = cur.fetchall()
        updated = 0
        for row in rows:
            start_dt, end_dt, is_ongoing = extract_from_periods(row["treatment_periods"])
            if start_dt is None and end_dt is None and not is_ongoing:
                continue
            cur.execute(
                """
                UPDATE patient_treatments
                SET treatment_start_date = %s, treatment_end_date = %s, treatment_is_ongoing = %s
                WHERE id = %s
                """,
                (start_dt, end_dt, is_ongoing, row["id"]),
            )
            updated += 1
        conn.commit()
        print(f"✅ {updated} enregistrement(s) mis à jour")

        # 3. Supprimer la colonne treatment_periods
        print("\n3️⃣ Suppression de la colonne treatment_periods...")
        cur.execute("ALTER TABLE patient_treatments DROP COLUMN IF EXISTS treatment_periods;")
        conn.commit()
        print("✅ Colonne treatment_periods supprimée")

        print("\n✅ Migration terminée avec succès.")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erreur: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
