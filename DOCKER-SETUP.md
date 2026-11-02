# Docker Setup - Move4Epilepsy API

Guide complet pour lancer l'API avec Docker et Docker Compose.

---

## 1. Prérequis

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git**
- **PostgreSQL** en cours d'exécution localement ou sur un serveur distant

### Installation

**macOS / Linux :**
```bash
# Docker Desktop (recommandé)
# Télécharge depuis https://www.docker.com/products/docker-desktop/

# Vérifier installation
docker --version
docker compose version
```

**Linux (via apt/yum) :**
```bash
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
```

---

## 2. Deux bases PostgreSQL distinctes

Le déploiement et les tests ne partagent pas la même base :

| Usage | Variable | Port local par défaut | Configuration |
|---|---|---:|---|
| API / déploiement | `DATABASE_URL` | `5432` | `.env` |
| Tests | `TEST_DATABASE_URL` | `5433` | `docker-compose.test.yml` |

Le compose principal ne contient pas de service PostgreSQL. Il lance seulement le service `api`, qui se connecte à la base configurée par `DATABASE_URL`.

## 3. Démarrage Rapide

### 2.1 Préparation

```bash
cd move4epilepsy-api

# Copier la configuration d'exemple
cp .env.example .env

# Générer une SECRET_KEY forte
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Éditer .env et renseigner les variables (clé secrète + DATABASE_URL)
nano .env  # ou ton éditeur
```

La variable `DATABASE_URL` doit pointer vers ta base PostgreSQL externe :

```env
# Base locale (accès depuis Docker Desktop sur Mac/Windows)
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/move4epilepsy

# Base locale (Linux)
DATABASE_URL=postgresql://user:password@172.17.0.1:5432/move4epilepsy

# Base distante
DATABASE_URL=postgresql://user:password@mon-serveur.com:5432/move4epilepsy
```

### 2.2 Lancer les containers

```bash
# Construire l'image & démarrer le service API
docker compose up -d --build api

# Appliquer le schéma (avant le premier démarrage et après une mise à jour)
docker compose run --rm --build api python -m scripts.migrate_patient_consent_workflow
docker compose run --rm api python -m scripts.migrate_medication_categories

# Vérifier l'état
docker compose ps

# Voir les logs
docker compose logs -f api
```

### 2.3 Vérifier que ça marche

```bash
# Health check
curl http://localhost:3003/health

# Documentation Swagger
open http://localhost:3003/docs

# API root
curl http://localhost:3003/
```

**Résultat attendu** :
```json
{
  "message": "Move4Epilepsy API",
  "version": "1.0.0",
  "docs": "/docs",
  "environment": "development"
}
```

---

## 4. Base PostgreSQL de test

```bash
docker compose -f docker-compose.test.yml up -d postgres-test
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/move4epilepsy_test \
  .venv/bin/pytest
docker compose -f docker-compose.test.yml down
```

La base de test utilise un volume séparé et le port `5433`. Elle ne doit jamais être utilisée comme `DATABASE_URL` du déploiement.

## 5. Services Disponibles

### API FastAPI
- **Port** : `http://localhost:3003`
- **Docs** : `http://localhost:3003/docs` (Swagger)
- **ReDoc** : `http://localhost:3003/redoc`
- **Health** : `http://localhost:3003/health`

---

## 4. Commandes Utiles

### Gestion des Containers

```bash
# Démarrer les services
docker compose up -d

# Arrêter les services
docker compose down

# Voir les logs
docker compose logs -f api

# Rebuilder les images
docker compose build --no-cache

# Redémarrer le service
docker compose restart api
```

### Créer les Utilisateurs de Test

```bash
# Via l'API (endpoints protégés)
curl -X POST http://localhost:3003/api/v1/auth/create-test-users \
  -H "Authorization: Bearer <admin_token>"

# Via le script (dans le container)
docker compose exec api python scripts/create_test_users.py
```

### Appliquer les changements de schéma

```bash
# Le dépôt utilise des scripts de migration explicites, pas Alembic.
docker compose run --rm api python -m scripts.migrate_patient_consent_workflow
docker compose run --rm api python -m scripts.migrate_medication_categories
```

### Voir les Variables d'Environnement

```bash
docker compose exec api env | grep -E "DATABASE_URL|SECRET_KEY|ENVIRONMENT"
```

---

## 5. Développement Local

### Mode Hot-Reload

Les volumes sont configurés pour recharger automatiquement les changements :

```bash
# Les fichiers dans app/ sont automatiquement reloadés
# Édite un fichier et rafraîchis le navigateur
```

### Ajouter des Dépendances

```bash
# 1. Ajouter à requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# 2. Rebuilder l'image
docker compose build api

# 3. Redémarrer le service
docker compose restart api
```

### Déboguer

```bash
# Logs détaillés
docker compose logs -f --tail=100 api

# Entrer dans le container
docker compose exec api /bin/bash

# Exécuter une commande Python
docker compose exec api python -c "print('Hello')"
```

---

## 6. Configuration Production

### Variables d'Environnement Production

```env
# .env.production
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generated_strong_key>
DATABASE_URL=postgresql://prod_user:prod_password@prod_host:5432/move4epilepsy
BACKEND_CORS_ORIGINS=https://move4epilepsy.com,https://www.move4epilepsy.com
FORCE_HTTPS=True
LOG_LEVEL=WARNING
```

### Lancer en Production

```bash
docker-compose -f docker-compose.yml \
  --env-file .env.production \
  up -d
```

### Reverse Proxy (Nginx)

```nginx
upstream api {
    server api:8000;
}

server {
    listen 443 ssl http2;
    server_name api.move4epilepsy.com;

    ssl_certificate /etc/letsencrypt/live/api.move4epilepsy.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.move4epilepsy.com/privkey.pem;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 7. Troubleshooting

### L'API ne démarre pas

```bash
# 1. Vérifier les logs
docker-compose logs api

# 2. Vérifier que DATABASE_URL est défini dans .env
docker-compose exec api env | grep DATABASE_URL

# 3. Reconstruire proprement
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### "Connection refused: database"

```bash
# Sur Mac/Windows : utiliser host.docker.internal au lieu de localhost
# DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/move4epilepsy

# Sur Linux : utiliser l'IP de la gateway Docker (souvent 172.17.0.1)
# DATABASE_URL=postgresql://user:pass@172.17.0.1:5432/move4epilepsy

# Vérifier que PostgreSQL accepte les connexions distantes
# Dans postgresql.conf : listen_addresses = '*'
# Dans pg_hba.conf : ajouter une règle pour l'IP Docker
```

### Permissions Docker

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Recharger les groupes
newgrp docker
```

---

## 8. Nettoyage & Housekeeping

```bash
# Supprimer les containers et images non utilisés
docker system prune -a

# Voir l'usage disque
docker system df
```

---

## 9. Ressources

- [Docker Docs](https://docs.docker.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

**Besoin d'aide ?** → Voir `SECURITY.md` pour la configuration de prod et `README.md` pour l'API
