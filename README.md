# Move4Epilepsy API

API FastAPI pour l'application Move4Epilepsy avec PostgreSQL.

## Bases de données

Le projet utilise deux bases PostgreSQL séparées :

- **Principale** : `DATABASE_URL`, utilisée par l'API et le déploiement.
- **Test** : `TEST_DATABASE_URL`, utilisée uniquement par pytest. Elle écoute par défaut sur le port `5433` et ne doit jamais être remplacée par l'URL principale.

La base principale peut être PostgreSQL local, distant ou managé. Le fichier `docker-compose.yml` ne lance pas PostgreSQL : il lance l'API et se connecte à la valeur de `DATABASE_URL`.

## Installation Rapide

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
# Éditer .env avec votre SECRET_KEY et votre DATABASE_URL principale
```

### 4. Lancer l'API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

L'API sera accessible sur :

- **API** : http://localhost:8002
- **Documentation Swagger** : http://localhost:8002/docs
- **Documentation ReDoc** : http://localhost:8002/redoc

## Déploiement avec Docker

1. Configurer `DATABASE_URL` vers la **base principale** et fournir une `SECRET_KEY` forte dans `.env`.
2. Démarrer le service API, dont le nom est `api` :

```bash
docker compose up -d --build api
docker compose logs -f api
```

Le conteneur API écoute sur le port `3003` de la machine et se connecte à la base indiquée par `DATABASE_URL`.

## Base de test

Démarrer uniquement la base de test :

```bash
docker compose -f docker-compose.test.yml up -d postgres-test
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/move4epilepsy_test \
  .venv/bin/pytest
```

Arrêter la base de test :

```bash
docker compose -f docker-compose.test.yml down
```

Ne lancez jamais les tests avec `DATABASE_URL` ou `TEST_DATABASE_URL` pointant vers la base principale.

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
