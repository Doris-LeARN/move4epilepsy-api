"""
Script de vérification complète et correction du schéma PostgreSQL
Compare minutieusement toutes les colonnes avec Supabase et corrige les différences
"""
import sys
import os
from typing import Dict, List, Set, Tuple
from sqlalchemy import inspect, text, MetaData, Table, Column as SQLColumn
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import String, Integer, Boolean, DateTime, Text, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import engine, Base, SessionLocal
from app.models import *  # Importe tous les modèles

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def get_supabase_client() -> Client:
    """Crée un client Supabase"""
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase package not installed")
    
    supabase_url = os.getenv("SUPABASE_URL") or "https://mmtqcpillfoildqtildi.supabase.co"
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "sb_publishable_A9G0QJJDQKhJ6iPwrQbiMQ_0v0LJtvK"
    
    return create_client(supabase_url, supabase_key)


def get_postgres_type(sqlalchemy_type):
    """Convertit un type SQLAlchemy en type PostgreSQL"""
    if isinstance(sqlalchemy_type, UUID):
        return "uuid"
    elif isinstance(sqlalchemy_type, String):
        length = getattr(sqlalchemy_type, 'length', None)
        if length:
            return f"varchar({length})"
        return "varchar"
    elif isinstance(sqlalchemy_type, Integer):
        return "integer"
    elif isinstance(sqlalchemy_type, Boolean):
        return "boolean"
    elif isinstance(sqlalchemy_type, DateTime):
        return "timestamp with time zone"
    elif isinstance(sqlalchemy_type, Text):
        return "text"
    elif isinstance(sqlalchemy_type, Numeric):
        precision = getattr(sqlalchemy_type, 'precision', 10)
        scale = getattr(sqlalchemy_type, 'scale', 2)
        return f"numeric({precision},{scale})"
    elif isinstance(sqlalchemy_type, JSONB):
        return "jsonb"
    elif isinstance(sqlalchemy_type, JSON):
        return "json"
    elif isinstance(sqlalchemy_type, ARRAY):
        item_type = getattr(sqlalchemy_type, 'item_type', String)
        return f"{get_postgres_type(item_type)}[]"
    else:
        return str(sqlalchemy_type).replace('()', '')


def get_column_default(column):
    """Extrait la valeur par défaut d'une colonne"""
    # Vérifier server_default d'abord
    if column.server_default is not None:
        if hasattr(column.server_default, 'text'):
            return column.server_default.text
        elif hasattr(column.server_default, 'arg'):
            arg = column.server_default.arg
            if hasattr(arg, 'compile'):
                try:
                    return arg.compile(dialect=postgresql.dialect())
                except:
                    return str(arg)
            return str(arg)
    
    # Vérifier default
    if column.default is not None:
        if hasattr(column.default, 'arg'):
            default_arg = column.default.arg
            if isinstance(default_arg, str):
                return f"'{default_arg}'"
            elif isinstance(default_arg, bool):
                return 'true' if default_arg else 'false'
            elif isinstance(default_arg, (int, float)):
                return str(default_arg)
            elif isinstance(default_arg, list):
                if isinstance(column.type, JSONB):
                    return "'[]'::jsonb"
                elif isinstance(column.type, ARRAY):
                    return "ARRAY[]::text[]"
                return "ARRAY[]"
            elif callable(default_arg):
                try:
                    result = default_arg()
                    if isinstance(result, str):
                        return f"'{result}'"
                    return str(result)
                except:
                    return None
            else:
                return str(default_arg)
    
    return None


def compare_table_with_model(db, table_name: str, model_class) -> List[str]:
    """Compare une table PostgreSQL avec son modèle SQLAlchemy"""
    inspector = inspect(engine)
    
    if not inspector.has_table(table_name):
        print(f"  ⚠️  Table {table_name} n'existe pas")
        return []
    
    # Obtenir les colonnes de la base de données
    db_columns = {}
    for col in inspector.get_columns(table_name):
        db_columns[col['name']] = {
            'type': str(col['type']),
            'nullable': col['nullable'],
            'default': str(col.get('default', '')) if col.get('default') else None
        }
    
    # Obtenir les colonnes du modèle
    model_table = model_class.__table__
    model_columns = {col.name: col for col in model_table.columns}
    
    alter_statements = []
    missing_columns = []
    different_columns = []
    
    print(f"\n📋 Table: {table_name}")
    print(f"   Colonnes dans DB: {len(db_columns)}")
    print(f"   Colonnes dans modèle: {len(model_columns)}")
    
    # Vérifier les colonnes manquantes
    for col_name, col in model_columns.items():
        if col_name not in db_columns:
            missing_columns.append(col_name)
            pg_type = get_postgres_type(col.type)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = get_column_default(col)
            
            alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {pg_type}'
            if default:
                alter_sql += f" DEFAULT {default}"
            alter_sql += f" {nullable}"
            
            alter_statements.append(alter_sql)
            print(f"  ➕ Colonne manquante: {col_name} ({pg_type})")
        else:
            # Vérifier les différences
            db_col = db_columns[col_name]
            pg_type = get_postgres_type(col.type)
            db_type = db_col['type'].lower()
            
            # Normaliser les types
            type_mapping = {
                'character varying': 'varchar',
                'timestamp without time zone': 'timestamp',
                'timestamp with time zone': 'timestamp with time zone',
            }
            
            normalized_db_type = db_type
            for old, new in type_mapping.items():
                if old in normalized_db_type:
                    normalized_db_type = normalized_db_type.replace(old, new)
            
            type_matches = (
                pg_type.lower() in normalized_db_type or
                normalized_db_type in pg_type.lower() or
                (pg_type.lower() == 'uuid' and 'uuid' in normalized_db_type) or
                (pg_type.lower() == 'jsonb' and 'jsonb' in normalized_db_type) or
                (pg_type.lower() == 'text' and 'text' in normalized_db_type) or
                (pg_type.lower() == 'varchar' and 'character varying' in normalized_db_type)
            )
            
            if not type_matches:
                different_columns.append((col_name, db_type, pg_type))
                print(f"  🔄 Type différent: {col_name} ({db_type} → {pg_type})")
            
            # Vérifier nullable
            if col.nullable != db_col['nullable']:
                different_columns.append((col_name, f"nullable={db_col['nullable']}", f"nullable={col.nullable}"))
                constraint = "DROP NOT NULL" if col.nullable else "SET NOT NULL"
                alter_sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" {constraint}'
                alter_statements.append(alter_sql)
                print(f"  🔄 Nullable différent: {col_name} ({'NULL' if col.nullable else 'NOT NULL'})")
    
    # Vérifier les colonnes en trop dans la DB (ne pas les supprimer, juste informer)
    extra_columns = set(db_columns.keys()) - set(model_columns.keys())
    if extra_columns:
        print(f"  ⚠️  Colonnes supplémentaires dans DB (non supprimées): {', '.join(extra_columns)}")
    
    return alter_statements


def check_patient_treatments_data(db, supabase: Client):
    """Vérifie pourquoi les données de patient_treatments ne sont pas migrées"""
    print("\n" + "=" * 70)
    print("🔍 Vérification des données patient_treatments")
    print("=" * 70)
    
    # Compter dans Supabase
    try:
        response = supabase.table("patient_treatments").select("id", count="exact").execute()
        supabase_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        print(f"📊 Enregistrements dans Supabase: {supabase_count}")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération depuis Supabase: {e}")
        return
    
    # Compter dans PostgreSQL
    try:
        result = db.execute(text("SELECT COUNT(*) FROM patient_treatments"))
        pg_count = result.scalar()
        print(f"📊 Enregistrements dans PostgreSQL: {pg_count}")
    except Exception as e:
        print(f"❌ Erreur lors du comptage PostgreSQL: {e}")
        return
    
    if supabase_count > pg_count:
        print(f"\n⚠️  {supabase_count - pg_count} enregistrement(s) manquant(s) dans PostgreSQL")
        print("\n💡 Causes possibles:")
        print("   1. RLS (Row Level Security) dans Supabase bloque l'accès")
        print("   2. Erreurs lors de la migration (vérifier les logs)")
        print("   3. Données ajoutées après la migration")
        
        # Essayer de récupérer quelques enregistrements pour voir
        try:
            sample = supabase.table("patient_treatments").select("*").limit(5).execute()
            if sample.data:
                print(f"\n📝 Exemple d'enregistrement Supabase:")
                print(f"   Colonnes: {list(sample.data[0].keys())}")
        except Exception as e:
            print(f"   ⚠️  Impossible de récupérer un échantillon: {e}")
    else:
        print("✅ Tous les enregistrements sont présents")


def main():
    """Vérifie et corrige toutes les tables"""
    print("🔍 Vérification Complète du Schéma PostgreSQL")
    print("=" * 70)
    
    db = SessionLocal()
    supabase = None
    
    try:
        if SUPABASE_AVAILABLE:
            supabase = get_supabase_client()
            print("✅ Connexion à Supabase réussie")
        
        # Liste de tous les modèles
        models_to_check = [
            ("users", User),
            ("user_profiles", UserProfile),
            ("medications", Medication),
            ("pharmacies", Pharmacy),
            ("pharmacy_stocks", PharmacyStock),
            ("patient_searches", PatientSearch),
            ("search_alerts", SearchAlert),
            ("patient_treatments", PatientTreatment),
            ("demand_analytics", DemandAnalytics),
            ("stockout_predictions", StockoutPrediction),
            ("user_opinions", UserOpinion),
            ("partnership_applications", PartnershipApplication),
            ("medicine_reports", MedicineReport),
            ("epilepsy_perceptions", EpilepsyPerception),
            ("chat_channels", ChatChannel),
            ("chat_messages", ChatMessage),
            ("message_reports", MessageReport),
            ("subscription_plans", SubscriptionPlan),
            ("country_pricing", CountryPricing),
            ("pharmacy_subscriptions", PharmacySubscription),
            ("subscription_payments", SubscriptionPayment),
            ("admin_actions_log", AdminActionLog),
            ("user_suspensions", UserSuspension),
            ("system_settings", SystemSetting),
            ("alerts", Alert),
            ("stockout_alerts", StockoutAlert),
        ]
        
        all_alter_statements = []
        
        print("\n🔍 Analyse des différences...")
        for table_name, model_class in models_to_check:
            try:
                alter_statements = compare_table_with_model(db, table_name, model_class)
                all_alter_statements.extend(alter_statements)
            except Exception as e:
                print(f"  ❌ Erreur pour {table_name}: {e}")
        
        # Vérifier les données de patient_treatments
        if supabase:
            check_patient_treatments_data(db, supabase)
        
        if not all_alter_statements:
            print("\n✅ Aucune différence détectée - le schéma est à jour!")
            return
        
        print("\n" + "=" * 70)
        print(f"📝 {len(all_alter_statements)} modification(s) à appliquer")
        print("\n⚠️  SQL à exécuter:")
        print("-" * 70)
        for stmt in all_alter_statements:
            print(stmt)
        print("-" * 70)
        
        response = input("\n⚠️  Appliquer ces modifications? (oui/non): ")
        if response.lower() not in ["oui", "o", "yes", "y"]:
            print("❌ Synchronisation annulée")
            return
        
        print("\n🔧 Application des modifications...")
        for stmt in all_alter_statements:
            try:
                db.execute(text(stmt))
                db.commit()
                print(f"  ✅ {stmt[:70]}...")
            except Exception as e:
                print(f"  ❌ Erreur: {stmt[:70]}...")
                print(f"     {e}")
                db.rollback()
        
        print("\n" + "=" * 70)
        print("✅ Vérification terminée!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
