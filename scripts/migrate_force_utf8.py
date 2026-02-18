"""
Migration avec conversion UTF-8 forcée - Version agressive
Traite toutes les strings comme latin-1 → UTF-8
"""
import sys
import os
import json

os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session
from app.database.base import SessionLocal
from app.core.config import settings

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def force_utf8_conversion(value):
    """Force la conversion latin-1 → UTF-8 de manière agressive"""
    if value is None:
        return None
    
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8', errors='replace')
        except:
            return value.decode('latin-1', errors='replace').encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    if isinstance(value, str):
        # Traiter TOUTE string comme si elle était en latin-1 mal interprétée
        try:
            # Encoder en latin-1 (ne peut pas échouer)
            bytes_latin1 = value.encode('latin-1', errors='replace')
            # Décoder en UTF-8
            utf8_string = bytes_latin1.decode('utf-8', errors='replace')
            return utf8_string
        except Exception as e:
            # Si ça échoue, nettoyer normalement
            return value.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    if isinstance(value, (list, dict)):
        # Récursif pour les structures
        if isinstance(value, list):
            return [force_utf8_conversion(v) for v in value]
        else:
            return {k: force_utf8_conversion(v) for k, v in value.items()}
    
    return value


def migrate_table_force_utf8(db: Session, supabase: Client, table_name: str, string_columns: list):
    """Migre avec conversion UTF-8 forcée"""
    print(f"\n📦 Migration: {table_name}")
    
    try:
        db.execute(text("SET client_encoding = 'UTF8'"))
        
        offset = 0
        total = 0
        
        while True:
            try:
                response = supabase.table(table_name).select("*").range(offset, offset + 50).execute()
            except Exception as e:
                print(f"  ⚠️  Erreur: {e}")
                break
            
            if not response.data:
                break
            
            for record in response.data:
                try:
                    # Convertir TOUTES les strings
                    cleaned_record = {}
                    for key, value in record.items():
                        if key in string_columns and value is not None:
                            cleaned_record[key] = force_utf8_conversion(value)
                        else:
                            cleaned_record[key] = value
                    
                    # Construire INSERT
                    cols = list(cleaned_record.keys())
                    vals = [f":{c}" for c in cols]
                    params = {c: cleaned_record[c] for c in cols}
                    
                    query = text(f"""
                        INSERT INTO "{table_name}" ({', '.join([f'"{c}"' for c in cols])})
                        VALUES ({', '.join(vals)})
                        ON CONFLICT (id) DO UPDATE SET
                        {', '.join([f'"{c}" = EXCLUDED."{c}"' for c in cols if c != 'id'])}
                    """)
                    
                    db.execute(query, params)
                    total += 1
                    
                except Exception as e:
                    print(f"  ⚠️  Erreur sur un record: {e}")
                    db.rollback()
                    continue
            
            db.commit()
            print(f"  ✅ {len(response.data)} migrés (total: {total})")
            
            if len(response.data) < 50:
                break
            offset += 50
        
        return total
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 0


def main():
    print("🚀 Migration avec conversion UTF-8 FORCÉE")
    print("=" * 60)
    
    if not SUPABASE_AVAILABLE:
        print("❌ Installe supabase: pip install supabase")
        return
    
    supabase_url = os.getenv("SUPABASE_URL", "https://mmtqcpillfoildqtildi.supabase.co")
    supabase_key = "sb_publishable_A9G0QJJDQKhJ6iPwrQbiMQ_0v0LJtvK"
    
    if not supabase_key:
        print("❌ SUPABASE_SERVICE_ROLE_KEY requis")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    db = SessionLocal()
    
    try:
        db.execute(text("SET client_encoding = 'UTF8'"))
        print("✅ PostgreSQL configuré en UTF8")
    except Exception as e:
        print(f"❌ Erreur PostgreSQL: {e}")
        return
    
    print("\n⚠️  Cette migration va UPSERT (mettre à jour) les données")
    response = input("Continuer? (oui/non): ")
    if response.lower() not in ["oui", "o", "yes", "y"]:
        return
    
    migrations = [
        # Tables de base
        ("medications", ["name", "dosage", "form"]),
        ("pharmacies", ["name", "address", "city", "commune", "arrondissement", "quartier",
                       "responsible_first_name", "responsible_last_name"]),
        ("user_profiles", ["username", "first_name", "last_name", "phone"]),
        # Stocks et recherches
        ("pharmacy_stocks", ["medication_name", "restock_delay"]),
        ("patient_searches", ["department", "commune", "arrondissement", "quartier"]),
        ("search_alerts", ["department", "commune", "arrondissement", "quartier", "contact_email", "contact_phone"]),
        # Traitements patients
        ("patient_treatments", ["dosage", "frequency", "notes", "location", "education_level", 
                               "minimum_salary", "employment_status", "treatment_duration",
                               "monthly_cost", "unit_price", "access_ease", "side_effects",
                               "difficulties", "additional_comments", "found_medication",
                               "pharmacies_visited", "waiting_time", "stockout_frequency",
                               "morning_pills", "noon_pills", "evening_pills",
                               "has_financial_resources", "alternative_medication_name",
                               "action_when_delay_unknown"]),
        # Analytics
        ("demand_analytics", ["department", "commune", "medication_name", "analysis_data"]),
        ("stockout_predictions", ["medication_name", "department", "commune", "prediction_data"]),
        # Avis et perceptions
        ("user_opinions", ["author", "content", "category"]),
        ("partnership_applications", ["organization_type", "organization_name", "contact_person",
                                     "email", "phone", "website", "address", "city", "postal_code",
                                     "description", "resources", "experience", "motivation"]),
        ("medicine_reports", ["medicament", "pharmacy_name", "address", "city", "postal_code",
                             "reporter_name", "reporter_phone"]),
        ("epilepsy_perceptions", ["age_range", "danger_level", "normal_life", "contagious",
                                  "witness_experience", "suggestions"]),
        # Chat
        ("chat_channels", ["name", "description", "type"]),
        ("chat_messages", ["content"]),
        ("message_reports", ["reason"]),
        # Abonnements
        ("subscription_plans", ["name", "country", "currency"]),
        ("country_pricing", ["country", "country_code", "currency"]),
        ("pharmacy_subscriptions", []),  # Pas de colonnes string
        ("subscription_payments", ["currency", "payment_method", "payment_provider", "transaction_id"]),
        # Administration
        ("admin_actions_log", ["action_type", "target_type"]),
        ("user_suspensions", ["reason"]),
        ("system_settings", ["key", "description"]),
        # Alertes
        ("alerts", ["type", "medication_name", "message", "recipient_type", "location"]),
        ("stockout_alerts", ["medication_name", "patient_location", "status"]),
    ]
    
    total = 0
    for table, cols in migrations:
        count = migrate_table_force_utf8(db, supabase, table, cols)
        total += count
    
    print(f"\n✅ Total: {total} enregistrements")
    db.close()


if __name__ == "__main__":
    main()
