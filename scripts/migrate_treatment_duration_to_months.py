"""
Migration: Changer treatment_duration de String à Integer (mois)
et simplifier treatment_periods pour utiliser des dates datetime ISO

Ce script modifie la colonne treatment_duration pour stocker un nombre de mois
au lieu d'une chaîne de caractères.
"""

import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration de la base de données
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'move4epilepsy'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def migrate_treatment_duration():
    """Migrer treatment_duration de String à Integer"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("🔄 Migration: Changement de treatment_duration de String à Integer (mois)")
        
        # Étape 1: Ajouter une colonne temporaire pour stocker les mois
        print("\n1️⃣ Ajout d'une colonne temporaire treatment_duration_months...")
        cur.execute("""
            ALTER TABLE patient_treatments 
            ADD COLUMN IF NOT EXISTS treatment_duration_months INTEGER;
        """)
        print("✅ Colonne temporaire ajoutée")
        
        # Étape 2: Calculer les mois depuis treatment_periods pour les enregistrements existants
        print("\n2️⃣ Calcul des mois depuis treatment_periods...")
        
        # D'abord, vérifier les types de données existants
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN treatment_periods IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN jsonb_typeof(treatment_periods) = 'array' THEN 1 END) as array_count,
                COUNT(CASE WHEN jsonb_typeof(treatment_periods) = 'object' THEN 1 END) as object_count
            FROM patient_treatments;
        """)
        stats = cur.fetchone()
        print(f"📊 Statistiques: Total={stats[0]}, NULL={stats[1]}, Array={stats[2]}, Object={stats[3]}")
        
        # Mettre à jour les enregistrements avec treatment_periods en format array
        cur.execute("""
            UPDATE patient_treatments
            SET treatment_duration_months = (
                SELECT 
                    CASE 
                        WHEN jsonb_typeof(treatment_periods) = 'array' 
                         AND jsonb_array_length(treatment_periods) > 0 THEN
                            -- Calculer depuis les dates dans treatment_periods (format array)
                            (
                                SELECT 
                                    EXTRACT(YEAR FROM AGE(
                                        COALESCE(
                                            (period->>'end_date')::timestamp,
                                            (period->>'endDateISO')::timestamp,
                                            CURRENT_TIMESTAMP
                                        ),
                                        COALESCE(
                                            (period->>'start_date')::timestamp,
                                            (period->>'startDateISO')::timestamp
                                        )
                                    )) * 12 +
                                    EXTRACT(MONTH FROM AGE(
                                        COALESCE(
                                            (period->>'end_date')::timestamp,
                                            (period->>'endDateISO')::timestamp,
                                            CURRENT_TIMESTAMP
                                        ),
                                        COALESCE(
                                            (period->>'start_date')::timestamp,
                                            (period->>'startDateISO')::timestamp
                                        )
                                    )) + 1
                                FROM jsonb_array_elements(treatment_periods) AS period
                                WHERE (period->>'start_date' IS NOT NULL OR period->>'startDateISO' IS NOT NULL)
                                ORDER BY COALESCE(
                                    (period->>'start_date')::timestamp,
                                    (period->>'startDateISO')::timestamp
                                ) ASC
                                LIMIT 1
                            )
                        WHEN jsonb_typeof(treatment_periods) = 'object' 
                         AND treatment_periods ? 'periods' 
                         AND jsonb_typeof(treatment_periods->'periods') = 'array'
                         AND jsonb_array_length(treatment_periods->'periods') > 0 THEN
                            -- Calculer depuis les dates dans treatment_periods (format object avec periods)
                            (
                                SELECT 
                                    EXTRACT(YEAR FROM AGE(
                                        COALESCE(
                                            (period->>'end_date')::timestamp,
                                            (period->>'endDateISO')::timestamp,
                                            CURRENT_TIMESTAMP
                                        ),
                                        COALESCE(
                                            (period->>'start_date')::timestamp,
                                            (period->>'startDateISO')::timestamp
                                        )
                                    )) * 12 +
                                    EXTRACT(MONTH FROM AGE(
                                        COALESCE(
                                            (period->>'end_date')::timestamp,
                                            (period->>'endDateISO')::timestamp,
                                            CURRENT_TIMESTAMP
                                        ),
                                        COALESCE(
                                            (period->>'start_date')::timestamp,
                                            (period->>'startDateISO')::timestamp
                                        )
                                    )) + 1
                                FROM jsonb_array_elements(treatment_periods->'periods') AS period
                                WHERE (period->>'start_date' IS NOT NULL OR period->>'startDateISO' IS NOT NULL)
                                ORDER BY COALESCE(
                                    (period->>'start_date')::timestamp,
                                    (period->>'startDateISO')::timestamp
                                ) ASC
                                LIMIT 1
                            )
                        ELSE NULL
                    END
            )
            WHERE treatment_periods IS NOT NULL
              AND (
                  (jsonb_typeof(treatment_periods) = 'array' AND jsonb_array_length(treatment_periods) > 0)
                  OR 
                  (jsonb_typeof(treatment_periods) = 'object' 
                   AND treatment_periods ? 'periods' 
                   AND jsonb_typeof(treatment_periods->'periods') = 'array'
                   AND jsonb_array_length(treatment_periods->'periods') > 0)
              );
        """)
        updated_count = cur.rowcount
        print(f"✅ {updated_count} enregistrement(s) mis à jour avec calcul depuis treatment_periods")
        
        # Étape 3: Supprimer l'ancienne colonne treatment_duration
        print("\n3️⃣ Suppression de l'ancienne colonne treatment_duration...")
        cur.execute("""
            ALTER TABLE patient_treatments 
            DROP COLUMN IF EXISTS treatment_duration;
        """)
        print("✅ Ancienne colonne supprimée")
        
        # Étape 4: Renommer la nouvelle colonne
        print("\n4️⃣ Renommage de treatment_duration_months en treatment_duration...")
        cur.execute("""
            ALTER TABLE patient_treatments 
            RENAME COLUMN treatment_duration_months TO treatment_duration;
        """)
        print("✅ Colonne renommée")
        
        # Commit des changements
        conn.commit()
        print("\n✅ Migration terminée avec succès!")
        
        # Vérification
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'patient_treatments'
              AND column_name = 'treatment_duration';
        """)
        result = cur.fetchone()
        if result:
            print(f"\n📊 Vérification: treatment_duration est maintenant de type {result[1]}")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Erreur lors de la migration: {e}")
        raise
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Migration: treatment_duration → Integer (mois)")
    print("=" * 70)
    migrate_treatment_duration()
