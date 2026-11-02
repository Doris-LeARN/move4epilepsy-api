# Déploiement Move4Epilepsy

Ce guide couvre les deux dépôts indépendants : `move4epilepsy-api` et
`move4epilepsy-frontend`. Le navigateur parle à l’API; seul le backend se
connecte à PostgreSQL. Aucun service PostgreSQL n’est démarré par les fichiers
Compose de production.

## 1. Prérequis

- Docker avec Docker Compose v2 sur l’hôte de déploiement.
- Une base PostgreSQL accessible depuis le conteneur API.
- Un nom DNS et un reverse proxy HTTPS pour l’API et le frontend.
- Les deux dépôts clonés sur l’hôte ou un pipeline capable de construire leurs images.

Ports publiés par défaut : API `3003` vers le port conteneur `3000`, frontend
`8080` vers le port conteneur `80`. Le reverse proxy termine TLS et transmet les
requêtes à ces ports.

## 2. PostgreSQL et configuration

Créer la base et son utilisateur selon les règles de l’hébergeur, puis autoriser
les connexions depuis l’hôte ou le réseau Docker. Ne pas utiliser la base de test
sur le déploiement : elle utilise `TEST_DATABASE_URL` et le port `5433`.

Créer un fichier d’environnement API **hors des dépôts Git**. Exemple de valeurs
à adapter :

```dotenv
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<clé aléatoire d'au moins 32 caractères>
DATABASE_URL=postgresql://<utilisateur>:<mot-de-passe>@<hôte>:5432/move4epilepsy
BACKEND_CORS_ORIGINS=https://app.example.com
ALLOWED_HOSTS=api.example.com,localhost,127.0.0.1
FORCE_HTTPS=True
SECURE_COOKIES=True
LOG_LEVEL=INFO
```

Générer une clé avec `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Dans `DATABASE_URL`, l’hôte doit être joignable **depuis le conteneur API**; ne
pas utiliser `localhost` pour une base installée hors de ce conteneur. Pour un
reverse proxy ou un fournisseur géré, remplacer les domaines et paramètres par
ceux de l’environnement. Garder `localhost` et `127.0.0.1` dans `ALLOWED_HOSTS`
pour le healthcheck interne du conteneur.

Créer séparément un fichier d’environnement frontend, également hors Git :

```dotenv
VITE_API_BASE_URL=https://api.example.com/api/v1
FRONTEND_PORT=8080
```

`VITE_API_BASE_URL` est intégrée aux fichiers JavaScript publics pendant le build.
N’y placer aucun secret. L’origine publique du frontend doit correspondre à une
valeur de `BACKEND_CORS_ORIGINS` (schéma et domaine exacts, sans chemin).

Dans les commandes ci-dessous, définir les chemins sécurisés vers ces deux
fichiers :

```bash
export API_ENV_FILE=/chemin/securise/api.env
export FRONTEND_ENV_FILE=/chemin/securise/frontend.env
```

## 3. Déployer l’API

Depuis la racine du dépôt `move4epilepsy-api` :

```bash
docker compose --env-file "$API_ENV_FILE" config --quiet
docker compose --env-file "$API_ENV_FILE" build api
```

Avant la première mise en service ou après une évolution du schéma, sauvegarder
la base, puis exécuter les migrations applicables à cette version :

```bash
docker compose --env-file "$API_ENV_FILE" run --rm api python -m scripts.migrate_patient_consent_workflow
docker compose --env-file "$API_ENV_FILE" run --rm api python -m scripts.migrate_subscription_checkout_fields
docker compose --env-file "$API_ENV_FILE" run --rm api python -m scripts.migrate_add_data_ownership
docker compose --env-file "$API_ENV_FILE" run --rm api python -m scripts.migrate_medication_categories
```

Pour réparer les accents du catalogue déjà stocké, lancer aussi la migration
ciblée ci-dessous. Elle est idempotente et ne modifie que les libellés connus :

```bash
docker compose --env-file "$API_ENV_FILE" run --rm api python -m scripts.migrate_medication_accents
```

Démarrer l’API et vérifier son état :

```bash
docker compose --env-file "$API_ENV_FILE" up -d api
docker compose --env-file "$API_ENV_FILE" ps
docker compose --env-file "$API_ENV_FILE" logs --tail=100 api
curl --fail http://127.0.0.1:3003/health
```

En production, `DEBUG=False` désactive Swagger. Utiliser `/health` pour le
healthcheck et le reverse proxy pour exposer l’API en HTTPS.

## 4. Déployer le frontend

Depuis la racine du dépôt `move4epilepsy-frontend` :

Le guide détaillé du frontend se trouve dans `DEPLOIEMENT.md` à la racine du
dépôt `move4epilepsy-frontend`.

```bash
docker compose --env-file "$FRONTEND_ENV_FILE" config --quiet
docker compose --env-file "$FRONTEND_ENV_FILE" up -d --build
docker compose --env-file "$FRONTEND_ENV_FILE" ps
docker compose --env-file "$FRONTEND_ENV_FILE" logs --tail=100 frontend
curl --fail --head http://127.0.0.1:8080
```

Le frontend est servi en statique par Nginx. Après toute modification de
`VITE_API_BASE_URL`, reconstruire l’image avec `--build`; redémarrer seulement
le conteneur ne modifie pas l’URL déjà intégrée au bundle.

## 5. Contrôles après déploiement

Remplacer les domaines d’exemple par les URLs HTTPS publiques :

```bash
curl --fail https://api.example.com/health
curl --fail https://api.example.com/api/v1/medications
curl --fail --head https://app.example.com
curl --include --request OPTIONS https://api.example.com/api/v1/medications \
  --header 'Origin: https://app.example.com' \
  --header 'Access-Control-Request-Method: GET'
```

La réponse CORS doit contenir `Access-Control-Allow-Origin: https://app.example.com`.
Ouvrir ensuite le frontend et vérifier un écran qui lit des données, par exemple
la recherche de médicaments.

## 6. Mise à jour et arrêt

Après avoir récupéré une version validée des deux dépôts, reconstruire et
redémarrer leurs services :

```bash
# Dans le dépôt API
docker compose --env-file "$API_ENV_FILE" build api
docker compose --env-file "$API_ENV_FILE" up -d api

# Dans le dépôt frontend
docker compose --env-file "$FRONTEND_ENV_FILE" up -d --build
```

Pour consulter les logs ou arrêter les services :

```bash
docker compose --env-file "$API_ENV_FILE" logs -f api
docker compose --env-file "$API_ENV_FILE" down

docker compose --env-file "$FRONTEND_ENV_FILE" logs -f frontend
docker compose --env-file "$FRONTEND_ENV_FILE" down
```

Ne jamais lancer `scripts/migrate_from_supabase.py` comme migration de routine :
ce script sert à une migration de données dédiée et peut vider des tables. Pour
les autres scripts de schéma, consulter `scripts/WORKFLOW.md` et confirmer qu’ils
sont nécessaires à la version déployée et qu’ils ciblent la bonne base.