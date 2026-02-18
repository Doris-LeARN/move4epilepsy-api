"""
Migration: Ajouter les colonnes pour gérer les délais de réapprovisionnement précis/imprécis

Nouvelles colonnes :
- is_restock_delay_precise: Boolean (le délai est-il précis ?)
- restock_delay_precise: String (délai précis si fourni, ex: "2-3 jours")
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

def migrate_add_restock_delay_fields():
    """Ajouter les colonnes pour les délais de réapprovisionnement"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("🔄 Migration: Ajout des colonnes pour délais de réapprovisionnement")
        
        # Étape 1: Ajouter is_restock_delay_precise
        print("\n1️⃣ Ajout de la colonne is_restock_delay_precise...")
        cur.execute("""
            ALTER TABLE patient_treatments 
            ADD COLUMN IF NOT EXISTS is_restock_delay_precise BOOLEAN;
        """)
        print("✅ Colonne is_restock_delay_precise ajoutée")
        
        # Étape 2: Ajouter restock_delay_precise
        print("\n2️⃣ Ajout de la colonne restock_delay_precise...")
        cur.execute("""
            ALTER TABLE patient_treatments 
            ADD COLUMN IF NOT EXISTS restock_delay_precise VARCHAR(255);
        """)
        print("✅ Colonne restock_delay_precise ajoutée")
        
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
              AND column_name IN ('is_restock_delay_precise', 'restock_delay_precise')
            ORDER BY column_name;
        """)
        results = cur.fetchall()
        if results:
            print(f"\n📊 Vérification des colonnes ajoutées:")
            for col_name, data_type, is_nullable in results:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
        
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
    print("🚀 Migration: Ajout colonnes délais de réapprovisionnement")
    print("=" * 70)
    migrate_add_restock_delay_fields()
