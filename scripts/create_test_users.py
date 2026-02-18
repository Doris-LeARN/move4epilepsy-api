"""
Script pour créer des utilisateurs de test de manière sécurisée
À exécuter manuellement en développement

Usage:
    cd move4epilepsy-api
    source venv/bin/activate
    python scripts/create_test_users.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.base import SessionLocal
from app.api.v1.auth import create_user
from app.core.dependencies import get_user_by_username
from app.models.user import UserProfile
from app.schemas.user import UserCreate


def create_test_users():
    """Crée des utilisateurs de test avec leurs profils"""
    db = SessionLocal()
    
    try:
        # Liste des utilisateurs de test à créer
        test_users = [
            {
                "username": "admin_test",
                "email": "admin@test.com",
                "password": "admin123456",
                "role": "admin",
                "first_name": "Admin",
                "last_name": "Test",
                "phone": "+22912345678",
            },
            {
                "username": "pharmacien_test",
                "email": "pharmacien@test.com",
                "password": "pharmacien123456",
                "role": "pharmacien",
                "first_name": "Pharmacien",
                "last_name": "Test",
                "phone": "+22912345679",
            },
            {
                "username": "medecin_test",
                "email": "medecin@test.com",
                "password": "medecin123456",
                "role": "medecin",
                "first_name": "Médecin",
                "last_name": "Test",
                "phone": "+22912345680",
            },
            {
                "username": "patient_test",
                "email": "patient@test.com",
                "password": "patient123456",
                "role": "patient",
                "first_name": "Patient",
                "last_name": "Test",
                "phone": "+22912345681",
            },
        ]
        
        created_users = []
        skipped_users = []
        
        print("🔐 Création des utilisateurs de test...\n")
        
        for user_data in test_users:
            username = user_data["username"]
            
            # Vérifier si l'utilisateur existe déjà
            existing_user = get_user_by_username(db, username)
            if existing_user:
                print(f"⚠️  {username} existe déjà (ID: {existing_user.id})")
                skipped_users.append(username)
                continue
            
            try:
                # Créer l'utilisateur
                user_create = UserCreate(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"],
                )
                user = create_user(db, user_create)
                
                # Créer le profil avec le rôle
                profile = UserProfile(
                    user_id=user.id,
                    username=user.username,
                    role=user_data["role"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    phone=user_data.get("phone", ""),
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)
                
                created_users.append({
                    "username": username,
                    "role": user_data["role"],
                    "id": str(user.id),
                })
                
                print(f"✅ Créé : {username} ({user_data['role']}) - ID: {user.id}")
                
            except Exception as e:
                db.rollback()
                print(f"❌ Erreur lors de la création de {username}: {e}")
                continue
        
        # Résumé
        print("\n" + "="*60)
        print("📊 RÉSUMÉ")
        print("="*60)
        print(f"✅ Créés : {len(created_users)}")
        print(f"⚠️  Ignorés (déjà existants) : {len(skipped_users)}")
        
        if created_users:
            print("\n👥 Utilisateurs créés :")
            for user in created_users:
                print(f"   - {user['username']} ({user['role']})")
        
        if skipped_users:
            print("\n⚠️  Utilisateurs déjà existants :")
            for username in skipped_users:
                print(f"   - {username}")
        
        print("\n" + "="*60)
        print("🔑 INFORMATIONS DE CONNEXION")
        print("="*60)
        print("\nVous pouvez maintenant vous connecter avec :")
        for user_data in test_users:
            if user_data["username"] not in skipped_users:
                print(f"\n{user_data['role'].upper()}:")
                print(f"  Username: {user_data['username']}")
                print(f"  Password: {user_data['password']}")
                print(f"  Email: {user_data['email']}")
        
        print("\n💡 Pour obtenir un token JWT, utilisez :")
        print("   curl -X POST 'http://localhost:8000/api/v1/auth/login' \\")
        print("     -H 'Content-Type: application/x-www-form-urlencoded' \\")
        print("     -d 'username=admin_test&password=admin123456'")
        
    except Exception as e:
        print(f"\n❌ Erreur générale : {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_users()
