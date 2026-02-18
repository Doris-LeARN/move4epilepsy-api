"""
Script de migration des données Supabase → PostgreSQL local
"""
import sys
import os
from typing import Dict, List, Any
from datetime import datetime
import json

# Configuration de l'encodage UTF-8
import locale
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform != 'win32':
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.base import SessionLocal, engine
from app.models import *
from app.core.config import settings

# Pour Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  Le client Supabase n'est pas installé. Installe-le avec: pip install supabase")


def get_supabase_client() -> Client:
    """Crée un client Supabase"""
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase package not installed")
    
    # Récupérer les variables d'environnement Supabase
    supabase_url = os.getenv("SUPABASE_URL") or "https://mmtqcpillfoildqtildi.supabase.co"
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "sb_publishable_A9G0QJJDQKhJ6iPwrQbiMQ_0v0LJtvK"
    
    if not supabase_key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY doit être défini dans les variables d'environnement.\n"
            "Pour obtenir la clé service role :\n"
            "1. Va sur https://supabase.com/dashboard\n"
            "2. Sélectionne ton projet\n"
            "3. Va dans Settings > API\n"
            "4. Copie la 'service_role key' (⚠️ NE PAS EXPOSER côté client)"
        )
    
    return create_client(supabase_url, supabase_key)


def clean_string_value(value: Any) -> str:
    """Nettoie une valeur string pour éviter les problèmes d'encodage"""
    if value is None:
        return None
    
    if isinstance(value, bytes):
        # Essayer UTF-8 d'abord
        try:
            decoded = value.decode('utf-8', errors='strict')
            return decoded
        except UnicodeDecodeError:
            # Si UTF-8 échoue, essayer latin-1 (Windows-1252)
            try:
                decoded = value.decode('latin-1', errors='replace')
                # Re-encoder en UTF-8 proprement
                return decoded.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            except:
                return value.decode('utf-8', errors='replace')
    
    if isinstance(value, str):
        # Vérifier si la string contient des caractères mal encodés
        try:
            # Essayer de détecter si c'est du latin-1 mal interprété comme UTF-8
            # Si la string contient des caractères bizarres, essayer de la convertir
            encoded_bytes = value.encode('latin-1', errors='replace')
            decoded_utf8 = encoded_bytes.decode('utf-8', errors='replace')
            
            # Si la conversion a changé quelque chose, utiliser la version corrigée
            if decoded_utf8 != value:
                return decoded_utf8
            
            # Sinon, nettoyer normalement
            return value.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        except:
            # Si tout échoue, retourner tel quel
            return value
    
    return str(value)


def clean_record(record: Dict) -> Dict:
    """Nettoie un enregistrement pour éviter les problèmes d'encodage"""
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, str):
            cleaned[key] = clean_string_value(value)
        elif isinstance(value, (list, dict)):
            # Pour les arrays et JSON, convertir en string puis parser
            try:
                if isinstance(value, list):
                    cleaned[key] = [clean_string_value(v) if isinstance(v, str) else v for v in value]
                else:
                    cleaned[key] = {k: clean_string_value(v) if isinstance(v, str) else v for k, v in value.items()}
            except:
                cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


def migrate_table(
    db: Session,
    supabase: Client,
    table_name: str,
    model_class,
    batch_size: int = 100,
    transform_func=None
) -> int:
    """
    Migre une table de Supabase vers PostgreSQL
    
    Args:
        db: Session SQLAlchemy
        supabase: Client Supabase
        table_name: Nom de la table dans Supabase
        model_class: Classe SQLAlchemy modèle
        batch_size: Taille des lots pour la pagination
        transform_func: Fonction optionnelle pour transformer les données
    
    Returns:
        Nombre d'enregistrements migrés
    """
    print(f"\n📦 Migration de la table: {table_name}")
    
    try:
        # Vider la table avant de migrer (optionnel, demander confirmation)
        print(f"  📥 Récupération des données depuis Supabase...")
        
        # Récupérer toutes les données depuis Supabase
        offset = 0
        total_migrated = 0
        total_errors = 0
        
        while True:
            try:
                response = supabase.table(table_name).select("*").range(offset, offset + batch_size - 1).execute()
            except Exception as e:
                print(f"  ⚠️  Erreur lors de la récupération: {e}")
                break
            
            if not response.data or len(response.data) == 0:
                break
            
            # Nettoyer et transformer les données AVANT insertion
            records = []
            for raw_record in response.data:
                try:
                    # Nettoyer l'encodage
                    cleaned = clean_record(raw_record)
                    
                    # Transformer si nécessaire
                    if transform_func:
                        cleaned = transform_func(cleaned)
                    
                    records.append(cleaned)
                except Exception as e:
                    print(f"  ⚠️  Erreur lors du nettoyage d'un enregistrement: {e}")
                    continue
            
            # Insérer dans PostgreSQL avec gestion d'encodage
            batch_inserted = 0
            batch_errors = 0
            
            for record in records:
                try:
                    # Nettoyer à nouveau avant insertion (sécurité supplémentaire)
                    cleaned_record = {}
                    for key, value in record.items():
                        if isinstance(value, str):
                            cleaned_record[key] = clean_string_value(value)
                        else:
                            cleaned_record[key] = value
                    
                    # Créer une instance du modèle
                    db_record = model_class(**cleaned_record)
                    db.add(db_record)
                    batch_inserted += 1
                    total_migrated += 1
                    
                except Exception as e:
                    batch_errors += 1
                    error_msg = str(e)
                    record_id = cleaned_record.get('id', 'N/A')
                    
                    # Afficher les premières erreurs en détail
                    if batch_errors <= 5:
                        print(f"  ⚠️  Erreur insertion record {record_id}: {error_msg}")
                        if batch_errors <= 2:
                            print(f"     Clés: {list(cleaned_record.keys())[:10]}")
                            print(f"     Valeurs (échantillon): {dict(list(cleaned_record.items())[:3])}")
                    
                    # Ne pas rollback ici - on continue avec les autres enregistrements
                    # Le rollback se fera seulement si le commit échoue
                    continue
            
            # Commit par batch
            try:
                db.commit()
                if batch_errors > 0:
                    print(f"  ✅ {batch_inserted} enregistrements migrés, {batch_errors} erreur(s) (total: {total_migrated})")
                    total_errors += batch_errors
                else:
                    print(f"  ✅ {batch_inserted} enregistrements migrés (total: {total_migrated})")
            except Exception as e:
                print(f"  ❌ Erreur lors du commit du batch: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()
                # Réessayer les enregistrements un par un
                print(f"  🔄 Réessai des enregistrements un par un...")
                for record in records:
                    try:
                        cleaned_record = {}
                        for key, value in record.items():
                            if isinstance(value, str):
                                cleaned_record[key] = clean_string_value(value)
                            else:
                                cleaned_record[key] = value
                        db_record = model_class(**cleaned_record)
                        db.add(db_record)
                        db.commit()
                        total_migrated += 1
                    except Exception as e2:
                        db.rollback()
                        print(f"    ⚠️  Échec record {cleaned_record.get('id', 'N/A')}: {e2}")
                break
            
            # Afficher un résumé des erreurs si beaucoup
            if batch_errors > 5:
                print(f"  ⚠️  {batch_errors} erreurs dans ce batch (seulement les 5 premières affichées)")
            
            # Si on a moins de batch_size enregistrements, on a fini
            if len(response.data) < batch_size:
                break
            
            offset += batch_size
        
        print(f"  ✅ Migration terminée: {total_migrated} enregistrements")
        
        # Afficher un avertissement si beaucoup d'erreurs
        if total_errors > 0:
            print(f"\n  ⚠️  ATTENTION: {total_errors} enregistrement(s) n'ont pas pu être migrés")
            print(f"     Exécute 'python scripts/diagnose_migration.py' pour identifier les problèmes")
        
        return total_migrated
        
    except Exception as e:
        print(f"  ❌ Erreur lors de la migration de {table_name}: {e}")
        db.rollback()
        return 0


def transform_user_profile(record: Dict) -> Dict:
    """Transforme un user_profile de Supabase vers notre modèle"""
    return {
        "id": record.get("id"),
        "user_id": record.get("user_id"),
        "username": record.get("username"),
        "role": record.get("role", "patient"),
        "first_name": record.get("first_name", ""),
        "last_name": record.get("last_name", ""),
        "phone": record.get("phone", ""),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def transform_medication(record: Dict) -> Dict:
    """Transforme un medication de Supabase vers notre modèle"""
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "dosage": record.get("dosage"),
        "form": record.get("form", "Comprimé"),
        "active": record.get("active", True),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def transform_pharmacy(record: Dict) -> Dict:
    """Transforme une pharmacy de Supabase vers notre modèle"""
    return {
        "id": record.get("id"),
        "pharmacy_id": record.get("pharmacy_id"),
        "name": record.get("name"),
        "license_number": record.get("license_number"),
        "email": record.get("email"),
        "phone": record.get("phone"),
        "address": record.get("address"),
        "city": record.get("city"),
        "postal_code": record.get("postal_code"),
        "country": record.get("country", "Bénin"),
        "department": record.get("department"),
        "commune": record.get("commune"),
        "arrondissement": record.get("arrondissement"),
        "quartier": record.get("quartier"),
        "responsible_first_name": record.get("responsible_first_name"),
        "responsible_last_name": record.get("responsible_last_name"),
        "user_id": record.get("user_id"),
        "active": record.get("active", True),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def migrate_users_from_auth(db: Session, supabase: Client) -> Dict[str, str]:
    """
    Migre les utilisateurs depuis auth.users de Supabase
    Retourne un mapping user_id (Supabase) -> user_id (PostgreSQL)
    """
    print("\n👤 Migration des utilisateurs depuis auth.users")
    
    try:
        # Récupérer les utilisateurs depuis Supabase Auth
        # Note: Cela nécessite la clé service_role
        response = supabase.auth.admin.list_users()
        
        if not hasattr(response, 'users') or not response.users:
            print("  ⚠️  Aucun utilisateur trouvé ou accès refusé")
            return {}
        
        user_mapping = {}
        total_migrated = 0
        
        for auth_user in response.users:
            try:
                # Vérifier si l'utilisateur existe déjà
                existing = db.query(User).filter(User.email == auth_user.email).first()
                if existing:
                    user_mapping[auth_user.id] = str(existing.id)
                    continue
                
                # Créer l'utilisateur
                # Note: On ne peut pas récupérer le mot de passe hashé depuis Supabase
                # Il faudra que les utilisateurs réinitialisent leur mot de passe
                # Pour l'instant, on crée avec un mot de passe temporaire
                from app.core.security import get_password_hash
                
                db_user = User(
                    id=auth_user.id,  # Garder le même UUID
                    email=auth_user.email,
                    username=auth_user.email.split("@")[0],  # Utiliser email comme username temporaire
                    hashed_password=get_password_hash("TEMPORARY_PASSWORD_RESET_REQUIRED"),
                    is_active=auth_user.banned_at is None,
                    is_superuser=False,
                    created_at=auth_user.created_at,
                    updated_at=auth_user.updated_at or auth_user.created_at,
                )
                
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                
                user_mapping[auth_user.id] = str(db_user.id)
                total_migrated += 1
                print(f"  ✅ Utilisateur migré: {auth_user.email}")
                
            except Exception as e:
                print(f"  ⚠️  Erreur lors de la migration de l'utilisateur {auth_user.email}: {e}")
                db.rollback()
                continue
        
        print(f"  ✅ {total_migrated} utilisateurs migrés")
        return user_mapping
        
    except Exception as e:
        print(f"  ❌ Erreur lors de la migration des utilisateurs: {e}")
        print(f"     Assure-toi d'utiliser la clé SERVICE_ROLE_KEY (pas ANON_KEY)")
        return {}


def main():
    """Fonction principale de migration"""
    print("🚀 Démarrage de la migration Supabase → PostgreSQL")
    print("=" * 60)
    
    if not SUPABASE_AVAILABLE:
        print("\n❌ Le package 'supabase' n'est pas installé.")
        print("   Installe-le avec: pip install supabase")
        return
    
    # Créer le client Supabase
    try:
        supabase = get_supabase_client()
        print("✅ Connexion à Supabase réussie")
    except Exception as e:
        print(f"\n❌ Erreur de connexion à Supabase: {e}")
        return
    
    # Connexion PostgreSQL
    db = SessionLocal()
    
    try:
        # Vérifier la connexion PostgreSQL
        db.execute(text("SELECT 1"))
        print("✅ Connexion à PostgreSQL réussie")
    except Exception as e:
        print(f"\n❌ Erreur de connexion à PostgreSQL: {e}")
        print(f"   Vérifie que DATABASE_URL dans .env est correct")
        return
    
    print("\n" + "=" * 60)
    print("📋 Tables à migrer:")
    print("  1. users (depuis auth.users)")
    print("  2. user_profiles")
    print("  3. medications")
    print("  4. pharmacies")
    print("  5. pharmacy_stocks")
    print("  6. patient_searches")
    print("  7. search_alerts")
    print("  8. patient_treatments")
    print("  9. demand_analytics")
    print("  10. stockout_predictions")
    print("  11. user_opinions")
    print("  12. partnership_applications")
    print("  13. medicine_reports")
    print("  14. epilepsy_perceptions")
    print("  15. chat_channels")
    print("  16. chat_messages")
    print("  17. message_reports")
    print("  18. subscription_plans")
    print("  19. country_pricing")
    print("  20. pharmacy_subscriptions")
    print("  21. subscription_payments")
    print("  22. admin_actions_log")
    print("  23. user_suspensions")
    print("  24. system_settings")
    print("  25. alerts")
    print("  26. stockout_alerts")
    print("=" * 60)
    
    print("\n⚠️  IMPORTANT:")
    print("   - Cette migration va VIDER les tables existantes")
    print("   - Les données seront réimportées avec le bon encodage UTF-8")
    print("   - Assure-toi d'avoir une sauvegarde si nécessaire")
    
    response = input("\n⚠️  Vider les tables et refaire la migration? (oui/non): ")
    if response.lower() not in ["oui", "o", "yes", "y"]:
        print("❌ Migration annulée")
        return
    
    # Vider les tables dans l'ordre inverse des dépendances
    print("\n🗑️  Vidage des tables existantes...")
    tables_to_clear = [
        # Nouvelles tables (sans dépendances)
        "stockout_alerts", "alerts", "system_settings", "user_suspensions",
        "admin_actions_log", "subscription_payments", "pharmacy_subscriptions",
        "country_pricing", "subscription_plans", "message_reports", "chat_messages",
        "chat_channels",
        # Tables existantes
        "epilepsy_perceptions", "medicine_reports", "partnership_applications",
        "user_opinions", "stockout_predictions", "demand_analytics",
        "patient_treatments", "search_alerts", "patient_searches",
        "pharmacy_stocks", "pharmacies", "medications",
        "user_profiles", "users"
    ]
    
    for table in tables_to_clear:
        try:
            db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            db.commit()
            print(f"  ✅ Table {table} vidée")
        except Exception as e:
            print(f"  ⚠️  Erreur lors du vidage de {table}: {e}")
            db.rollback()
    
    # Migration des utilisateurs
    user_mapping = migrate_users_from_auth(db, supabase)
    
    # Migration des tables dans l'ordre des dépendances
    migrations = [
        # Tables de base
        ("user_profiles", UserProfile, transform_user_profile),
        ("medications", Medication, transform_medication),
        ("pharmacies", Pharmacy, transform_pharmacy),
        # Tables dépendantes de pharmacies
        ("pharmacy_stocks", PharmacyStock, None),
        ("pharmacy_subscriptions", PharmacySubscription, None),
        ("subscription_payments", SubscriptionPayment, None),
        # Tables de recherche
        ("patient_searches", PatientSearch, None),
        ("search_alerts", SearchAlert, None),
        ("patient_treatments", PatientTreatment, None),
        # Analytics
        ("demand_analytics", DemandAnalytics, None),
        ("stockout_predictions", StockoutPrediction, None),
        # Avis et perceptions
        ("user_opinions", UserOpinion, None),
        ("partnership_applications", PartnershipApplication, None),
        ("medicine_reports", MedicineReport, None),
        ("epilepsy_perceptions", EpilepsyPerception, None),
        # Chat
        ("chat_channels", ChatChannel, None),
        ("chat_messages", ChatMessage, None),
        ("message_reports", MessageReport, None),
        # Abonnements
        ("subscription_plans", SubscriptionPlan, None),
        ("country_pricing", CountryPricing, None),
        # Administration
        ("admin_actions_log", AdminActionLog, None),
        ("user_suspensions", UserSuspension, None),
        ("system_settings", SystemSetting, None),
        # Alertes
        ("alerts", Alert, None),
        ("stockout_alerts", StockoutAlert, None),
    ]
    
    total_migrated = 0
    for table_name, model_class, transform_func in migrations:
        count = migrate_table(db, supabase, table_name, model_class, transform_func=transform_func)
        total_migrated += count
    
    print("\n" + "=" * 60)
    print(f"✅ Migration terminée!")
    print(f"   Total: {total_migrated} enregistrements migrés")
    print("\n⚠️  IMPORTANT:")
    print("   - Les utilisateurs ont un mot de passe temporaire")
    print("   - Ils devront réinitialiser leur mot de passe")
    print("   - Vérifie les données migrées dans PostgreSQL")
    print("=" * 60)
    
    db.close()


if __name__ == "__main__":
    main()
