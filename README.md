# Move4Epilepsy API

API FastAPI pour l'application Move4Epilepsy avec PostgreSQL.

## 🚀 Installation Rapide (URGENCE)

### 1. Créer la base de données PostgreSQL

```bash
# Via psql
createdb move4epilepsy

# Ou via SQL
psql -U postgres
CREATE DATABASE move4epilepsy;
```

### 2. Installer les dépendances

```bash
cd move4epilepsy-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec votre DATABASE_URL
```

### 4. Lancer l'API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera accessible sur :
- **API** : http://localhost:8000
- **Documentation Swagger** : http://localhost:8000/docs
- **Documentation ReDoc** : http://localhost:8000/redoc

### 5. Créer les utilisateurs de test

```bash
# Option 1 : Via l'API (nécessite d'être admin)
curl -X POST "http://localhost:8000/api/v1/auth/create-test-users" \
  -H "Authorization: Bearer <votre_token_admin>" \
  -H "Content-Type: application/json"

# Option 2 : Via le script Python (recommandé)
python scripts/create_test_users.py
```

## 📋 Endpoints Disponibles

### Authentification
- `POST /api/v1/auth/register` - Enregistrer un nouvel utilisateur
- `POST /api/v1/auth/login` - Se connecter
- `GET /api/v1/auth/me` - Obtenir les informations de l'utilisateur actuel
- `GET /api/v1/auth/me/profile` - Obtenir le profil de l'utilisateur
- `POST /api/v1/auth/create-test-users` - Créer des utilisateurs de test (admin uniquement)

**Alternative : Script Python** (recommandé pour le développement)
```bash
python scripts/create_test_users.py
```

## 🗄️ Structure de la Base de Données

Les tables sont créées automatiquement au démarrage. Modèles inclus :

- `users` - Utilisateurs
- `user_profiles` - Profils avec rôles
- `medications` - Médicaments
- `pharmacies` - Pharmacies
- `pharmacy_stocks` - Stocks des pharmacies
- `patient_searches` - Recherches patients
- `search_alerts` - Alertes de recherche
- `patient_treatments` - Traitements patients
- `demand_analytics` - Analytics de demande
- `stockout_predictions` - Prédictions de rupture
- `user_opinions` - Avis utilisateurs
- `partnership_applications` - Candidatures partenariats
- `medicine_reports` - Signalements médicaments
- `epilepsy_perceptions` - Perceptions épilepsie

## 🔧 Configuration

Le fichier `.env` doit contenir :
```env
DATABASE_URL=postgresql://username:password@localhost:5432/move4epilepsy
```

## 📝 Notes

- Les tables sont créées automatiquement au démarrage en développement
- Pour la production, utiliser Alembic pour les migrations
- Les mots de passe sont hashés avec bcrypt
- Les tokens JWT expirent après 30 minutes par défaut

**Migration Supabase → PostgreSQL, schéma, encodage :** tout est dans `scripts/WORKFLOW.md`.
