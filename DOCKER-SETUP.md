# 🐳 Docker Setup - Move4Epilepsy API

Guide complet pour lancer l'API avec Docker et Docker Compose.

---

## 1. Prérequis

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git**

### Installation

**macOS / Linux :**
```bash
# Docker Desktop (recommandé)
# Télécharge depuis https://www.docker.com/products/docker-desktop/

# Vérifier installation
docker --version
docker-compose --version
```

**Linux (via apt/yum) :**
```bash
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
```

---

## 2. Démarrage Rapide

### 2.1 Préparation

```bash
cd move4epilepsy-api

# Copier la configuration d'exemple
cp .env.example .env

# Générer une SECRET_KEY forte
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Éditer .env et coller la clé générée
nano .env  # ou ton éditeur
```

### 2.2 Lancer les containers

```bash
# Construire les images & démarrer
docker-compose up -d

# Vérifier l'état
docker-compose ps

# Voir les logs
docker-compose logs -f api
```

### 2.3 Vérifier que ça marche

```bash
# Health check
curl http://localhost:8000/health

# Documentation Swagger
open http://localhost:8000/docs

# API root
curl http://localhost:8000/
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

## 3. Services Disponibles

### API FastAPI
- **Port** : `http://localhost:8000`
- **Docs** : `http://localhost:8000/docs` (Swagger)
- **ReDoc** : `http://localhost:8000/redoc`
- **Health** : `http://localhost:8000/health`

### PostgreSQL Database
- **Host** : `localhost:5432`
- **User** : `postgres`
- **Password** : `postgres` (par défaut dans .env)
- **Database** : `move4epilepsy`

**Connexion depuis le terminal :**
```bash
psql -h localhost -U postgres -d move4epilepsy
```

### PgAdmin (optionnel)
- **URL** : `http://localhost:5050`
- **Email** : `admin@example.com`
- **Password** : `admin`

**Activer PgAdmin :**
```bash
docker-compose --profile dev up -d
```

---

## 4. Commandes Utiles

### Gestion des Containers

```bash
# Démarrer les services
docker-compose up -d

# Arrêter les services
docker-compose down

# Arrêter et supprimer volumes (attention! perte de données)
docker-compose down -v

# Voir les logs
docker-compose logs -f api
docker-compose logs -f db

# Rebuilder les images
docker-compose build --no-cache

# Redémarrer un service
docker-compose restart api
```

### Accès à la Base de Données

```bash
# Terminal PostgreSQL dans le container
docker-compose exec db psql -U postgres -d move4epilepsy

# Exemple: lister les tables
\dt

# Quitter psql
\q
```

### Créer les Utilisateurs de Test

```bash
# Via l'API (endpoints protégés)
curl -X POST http://localhost:8000/api/v1/auth/create-test-users \
  -H "Authorization: Bearer <admin_token>"

# Via le script (dans le container)
docker-compose exec api python scripts/create_test_users.py
```

### Exécuter des Migrations

```bash
# Alembic migrations
docker-compose exec api alembic upgrade head

# Créer une nouvelle migration
docker-compose exec api alembic revision --autogenerate -m "Description"
```

### Voir les Variables d'Environnement

```bash
docker-compose exec api env | grep -i move
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
docker-compose build api

# 3. Redémarrer le service
docker-compose restart api
```

### Déboguer

```bash
# Logs détaillés
docker-compose logs -f --tail=100 api

# Entrer dans le container
docker-compose exec api /bin/bash

# Exécuter une commande Python
docker-compose exec api python -c "print('Hello')"
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
# Utiliser un fichier .env séparé
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

## 7. Gestion des Données

### Backups PostgreSQL

```bash
# Backup complet
docker-compose exec db pg_dump -U postgres move4epilepsy > backup.sql

# Restauration
docker-compose exec -T db psql -U postgres move4epilepsy < backup.sql
```

### Volumes

```bash
# Lister les volumes
docker volume ls

# Inspecter un volume
docker volume inspect move4epilepsy-api_postgres_data

# Supprimer les volumes (attention!)
docker volume prune
```

---

## 8. Troubleshooting

### L'API ne démarre pas

```bash
# 1. Vérifier les logs
docker-compose logs api

# 2. Reconstruire proprement
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# 3. Vérifier les variables d'env
docker-compose exec api env | grep SECRET_KEY
```

### "port 5432 already in use"

```bash
# Trouver le process utilisant le port
lsof -i :5432

# Tuer le process (macOS)
kill -9 <PID>

# Ou modifier le port dans docker-compose.yml
# ports:
#   - "5433:5432"
```

### "Connection refused: database"

```bash
# Attendre que la DB soit prête
docker-compose logs db

# DB health check
docker-compose exec db pg_isready -U postgres
```

### Permissions Docker

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Recharger les groupes
newgrp docker
```

---

## 9. Nettoyage & Housekeeping

```bash
# Supprimer les containers et images non utilisés
docker system prune -a

# Supprimer les volumes non utilisés
docker volume prune

# Voir l'usage disque
docker system df
```

---

## 10. Ressources

- [Docker Docs](https://docs.docker.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

**Besoin d'aide ?** → Voir `SECURITY.md` pour la configuration de prod et `README.md` pour l'API
