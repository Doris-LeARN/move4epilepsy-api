# 🔐 Système de Sécurité JWT et Utilisateurs Tests

## ✅ Ce qui existe déjà

### 1. **Authentification JWT**

L'API FastAPI utilise déjà un système complet d'authentification JWT :

**Fichiers clés** :
- `app/core/security.py` - Création et validation des tokens JWT
- `app/api/v1/auth.py` - Endpoints d'authentification
- `app/core/permissions.py` - Gestion des rôles et permissions

**Fonctionnalités** :
- ✅ Création de tokens JWT avec expiration
- ✅ Validation des tokens sur chaque requête
- ✅ Hash des mots de passe avec bcrypt
- ✅ Gestion des rôles (admin, medecin, pharmacien, patient)

---

### 2. **Création d'utilisateurs tests**

**Endpoint existant** : `POST /api/v1/auth/create-test-users`

**Utilisateurs créés** :
- `admin_test` / `admin123456` (admin)
- `pharmacien_test` / `pharmacien123456` (pharmacien)
- `medecin_test` / `medecin123456` (medecin)
- `patient_test` / `patient123456` (patient)

**⚠️ PROBLÈME DE SÉCURITÉ** : Cet endpoint n'est **PAS protégé** ! N'importe qui peut créer des utilisateurs de test.

---

### 3. **Système de permissions**

**Dépendances disponibles** :
- `require_admin()` - Seuls les admins
- `require_medecin()` - Médecins et admins
- `require_pharmacien()` - Pharmaciens et admins
- `require_role(["role1", "role2"])` - Rôles personnalisés

**Exemple d'utilisation** :
```python
@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin)
):
    # Seuls les admins peuvent accéder
    return {"message": "Admin only"}
```

---

## 🔒 Comment ça fonctionne

### 1. **Login et obtention du token**

```bash
# 1. Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin_test&password=admin123456"

# Réponse :
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. **Utilisation du token**

```bash
# 2. Utiliser le token pour accéder à un endpoint protégé
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. **Vérification automatique**

À chaque requête avec le header `Authorization: Bearer <token>` :
1. Le token est décodé
2. Le username est extrait (`payload.get("sub")`)
3. L'utilisateur est récupéré depuis la base de données
4. Le profil (avec le rôle) est chargé
5. Les permissions sont vérifiées selon les dépendances

---

## 🛡️ Sécurisation des endpoints

### Exemples de protection

**1. Endpoint public (anonyme autorisé)** :
```python
@router.post("/treatments")
async def create_treatment(
    treatment_data: PatientTreatmentCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    # current_user peut être None (anonyme)
    # Mais si un token est fourni, l'utilisateur est identifié
    pass
```

**2. Endpoint authentifié (login requis)** :
```python
@router.get("/users/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user_required)
):
    # current_user est toujours défini (sinon erreur 401)
    return current_user
```

**3. Endpoint avec rôle spécifique** :
```python
@router.get("/admin/dashboard")
async def admin_dashboard(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin)
):
    # Seuls les admins peuvent accéder (erreur 403 sinon)
    return {"data": "admin only"}
```

---

## ⚠️ Améliorations de sécurité nécessaires

### 1. **Protéger l'endpoint de création d'utilisateurs tests**

**Problème actuel** :
```python
@router.post("/create-test-users")  # ❌ PAS PROTÉGÉ !
async def create_test_users(db: Session = Depends(get_db)):
    # N'importe qui peut créer des utilisateurs !
```

**Solution recommandée** :

**Option A : Limiter à l'environnement de développement**
```python
from app.core.config import settings

@router.post("/create-test-users", status_code=status.HTTP_201_CREATED)
async def create_test_users(
    db: Session = Depends(get_db),
    # Vérifier que c'est en développement
    _: None = Depends(lambda: None if settings.ENVIRONMENT == "development" else HTTPException(403))
):
    if settings.ENVIRONMENT != "development":
        raise HTTPException(403, "Only available in development")
    # ... reste du code
```

**Option B : Protéger avec un token admin**
```python
@router.post("/create-test-users", status_code=status.HTTP_201_CREATED)
async def create_test_users(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),  # ✅ Seuls les admins
    db: Session = Depends(get_db)
):
    # ... reste du code
```

**Option C : Utiliser une clé API secrète**
```python
@router.post("/create-test-users", status_code=status.HTTP_201_CREATED)
async def create_test_users(
    secret_key: str = Header(..., alias="X-Secret-Key"),
    db: Session = Depends(get_db)
):
    if secret_key != settings.TEST_USERS_SECRET_KEY:
        raise HTTPException(403, "Invalid secret key")
    # ... reste du code
```

---

### 2. **Sécuriser les tables sensibles**

**Tables à protéger** :
- `users` - Données utilisateurs
- `user_profiles` - Profils et rôles
- `pharmacies` - Informations pharmacies
- `pharmacy_stocks` - Stocks (données sensibles)
- `patient_treatments` - Données patients (RGPD)

**Stratégie recommandée** :

**A. Au niveau des endpoints** (déjà fait) :
- ✅ Utiliser `get_current_user` pour vérifier l'authentification
- ✅ Utiliser `require_admin`, `require_medecin`, etc. pour les rôles
- ✅ Utiliser `get_current_user_optional` pour les endpoints anonymes

**B. Au niveau de la base de données** (à ajouter) :
- Créer des vues PostgreSQL avec Row Level Security (RLS)
- Limiter l'accès direct aux tables sensibles
- Utiliser des triggers pour l'audit

**C. Au niveau de l'application** :
- Filtrer les données selon le rôle de l'utilisateur
- Ne pas exposer les champs sensibles (mots de passe, tokens, etc.)

---

### 3. **Améliorer la gestion des tokens**

**Problèmes actuels** :
- Pas de refresh token (le token expire, il faut se reconnecter)
- Pas de blacklist des tokens (un token reste valide jusqu'à expiration)
- Pas de rotation des clés secrètes

**Solutions recommandées** :

**A. Ajouter un refresh token** :
```python
@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str = Body(...),
    db: Session = Depends(get_db)
):
    # Valider le refresh token
    # Créer un nouveau access token
    pass
```

**B. Ajouter une blacklist** :
```python
# Table pour stocker les tokens révoqués
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    token_id = Column(String, primary_key=True)
    expires_at = Column(DateTime)

# Vérifier dans get_current_user
def get_current_user(...):
    # Vérifier si le token est dans la blacklist
    if is_token_blacklisted(token):
        raise HTTPException(401, "Token revoked")
```

---

## 📝 Exemple complet : Endpoint sécurisé

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.auth import get_current_user
from app.core.permissions import require_admin
from app.models.user import User

router = APIRouter()

@router.get("/sensitive-data")
async def get_sensitive_data(
    current_user: User = Depends(get_current_user),  # ✅ Auth requise
    _: None = Depends(require_admin)  # ✅ Admin seulement
):
    """
    Endpoint sécurisé :
    1. L'utilisateur doit être authentifié (JWT valide)
    2. L'utilisateur doit être admin
    3. Les données sont filtrées selon le rôle
    """
    # Récupérer les données sensibles
    sensitive_data = get_data_from_db()
    
    # Filtrer selon le rôle (exemple)
    if current_user.profile.role == "admin":
        return sensitive_data  # Tout voir
    else:
        return filter_sensitive_fields(sensitive_data)  # Voir moins
```

---

## 🧪 Créer des utilisateurs tests (sécurisé)

### Méthode recommandée : Script Python

**Créer un script** : `scripts/create_test_users.py`

```python
"""
Script pour créer des utilisateurs de test de manière sécurisée
À exécuter manuellement en développement
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.base import SessionLocal
from app.api.v1.auth import create_user
from app.models.user import UserProfile
from app.schemas.user import UserCreate

def create_test_users():
    db = SessionLocal()
    try:
        test_users = [
            {
                "username": "admin_test",
                "email": "admin@test.com",
                "password": "admin123456",
                "role": "admin",
            },
            # ... autres utilisateurs
        ]
        
        for user_data in test_users:
            # Vérifier si existe déjà
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if existing:
                print(f"⚠️  {user_data['username']} existe déjà")
                continue
            
            # Créer l'utilisateur
            user_create = UserCreate(**user_data)
            user = create_user(db, user_create)
            
            # Créer le profil
            profile = UserProfile(
                user_id=user.id,
                username=user.username,
                role=user_data["role"],
                first_name=user_data["username"].split("_")[0].capitalize(),
                last_name="Test",
            )
            db.add(profile)
            db.commit()
            
            print(f"✅ Créé : {user_data['username']} ({user_data['role']})")
    
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()
```

**Utilisation** :
```bash
cd move4epilepsy-api
source venv/bin/activate
python scripts/create_test_users.py
```

---

## ✅ Checklist de sécurité

- [x] JWT implémenté avec expiration
- [x] Hash des mots de passe avec bcrypt
- [x] Système de rôles et permissions
- [x] Endpoints protégés avec dépendances
- [ ] **Protéger `/auth/create-test-users`** (à faire)
- [ ] Ajouter refresh tokens (optionnel)
- [ ] Ajouter blacklist des tokens (optionnel)
- [ ] Ajouter audit log (optionnel)
- [ ] Limiter les tentatives de login (rate limiting)
- [ ] Chiffrer les données sensibles en base (optionnel)

---

## 🎯 Recommandations

1. **Immédiat** : Protéger `/auth/create-test-users` avec `require_admin` ou le limiter au développement
2. **Court terme** : Ajouter un script Python pour créer les utilisateurs tests
3. **Moyen terme** : Implémenter refresh tokens et blacklist
4. **Long terme** : Ajouter Row Level Security (RLS) au niveau PostgreSQL

---

**✅ Conclusion** : Le système JWT existe déjà et fonctionne bien. Il faut juste sécuriser l'endpoint de création d'utilisateurs tests et améliorer la gestion des tokens si nécessaire.
