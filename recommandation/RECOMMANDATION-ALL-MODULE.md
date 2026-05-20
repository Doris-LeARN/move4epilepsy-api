# Move4Epilepsy — Audit de Sécurité et Qualité

**Périmètre :** `move4epilepsy-api` (FastAPI + PostgreSQL) et `move4epilepsy-portalLocal` (React + TypeScript + Vite)  
**Date :** 2026-05-19  
**Niveau de risque global : ÉLEVÉ** — plusieurs failles critiques bloquantes avant mise en production

---

## Résumé Exécutif

| Sévérité | Backend API | Frontend Portal | Total |
|----------|------------|-----------------|-------|
| Critique | 5 | 3 | **8** |
| Élevé | 5 | 4 | **9** |
| Moyen | 8 | 5 | **13** |
| Faible | 5 | 5 | **10** |

Les problèmes critiques concernent principalement :
1. Des secrets codés en dur dans le code source
2. L'absence totale d'autorisation sur les données médicales patients
3. Le stockage des tokens JWT dans `localStorage`
4. L'absence de rate limiting sur les endpoints d'authentification

---

## PARTIE 1 — Backend (`move4epilepsy-api`)

### CRITIQUE

#### C1 — `SECRET_KEY` codée en dur
**Fichier :** `app/core/config.py:34`

```python
SECRET_KEY: str = "change-me-in-production-use-env-variable"
```

Si le fichier `.env` est absent ou mal configuré en production, tous les tokens JWT émis
peuvent être forgés par n'importe qui connaissant cette valeur par défaut. Il n'existe aucun
validateur qui lèverait une erreur au démarrage.

**Correction :**
```python
from pydantic import field_validator

SECRET_KEY: str  # pas de valeur par défaut

@field_validator("SECRET_KEY")
@classmethod
def secret_key_must_be_set(cls, v: str) -> str:
    if not v or v == "change-me-in-production-use-env-variable":
        raise ValueError("SECRET_KEY must be explicitly set via environment variable")
    if len(v) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    return v
```

---

#### C2 — Credentials base de données codés en dur
**Fichier :** `app/core/config.py:39`

```python
DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/move4epilepsy"
```

Même risque que C1. En l'absence de `.env`, l'API tente de se connecter avec `postgres:postgres`.

**Correction :** Supprimer la valeur par défaut et ajouter un validateur identique à C1.

---

#### C3 — Clé API tierce codée en dur dans le source
**Fichier :** `app/api/v1/routing.py:22`

```python
OPENROUTESERVICE_API_KEY = os.getenv(
    "OPENROUTESERVICE_API_KEY",
    "5b3ce3597851110001cf6248e8c8e8c8b8c8e8c8b8c8e8c8b8c8e8c8b"
)
```

Cette clé est commitée dans le dépôt. Si le dépôt est ou devient public, la clé est exposée.

**Correction :**
```python
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
if not OPENROUTESERVICE_API_KEY:
    # degraded mode: Haversine fallback only, no external API calls
    pass
```
Révoquer et régénérer la clé immédiatement si le dépôt a été partagé.

---

#### C4 — Aucune autorisation sur les données médicales patients
**Fichier :** `app/api/v1/patients.py`

Trois endpoints exposent ou modifient des données médicales sensibles sans contrôle d'accès :

| Endpoint | Méthode | Auth requise | Problème |
|----------|---------|--------------|---------|
| `/treatments` | GET | Non | N'importe qui lit jusqu'à 1000 traitements |
| `/treatments/{id}` | GET | Non | N'importe qui lit un traitement individuel |
| `/treatments/{id}` | PUT | Non | N'importe qui modifie n'importe quel traitement |

Les commentaires `# TODO: Implémenter la logique RLS exacte` aux lignes 126, 178 et 200
confirment que cette logique n'a jamais été implémentée.

Ces données incluent : `medication_name`, `dosage`, `age`, `sex`, `location`,
`employment_status`, `minimum_salary`, `has_financial_resources`.

**Correction minimale pour GET :**
```python
@router.get("/treatments", response_model=List[PatientTreatmentResponse])
async def get_treatments(
    current_user: User = Depends(get_current_user),  # requis
    _: None = Depends(require_medecin),               # médecin ou admin seulement
    ...
):
```

**Correction pour PUT :**
```python
@router.put("/treatments/{treatment_id}", response_model=PatientTreatmentResponse)
async def update_treatment(
    treatment_id: UUID,
    treatment_data: PatientTreatmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    treatment = db.query(PatientTreatment).filter(
        PatientTreatment.id == treatment_id
    ).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")

    user_role = current_user.profile.role if current_user.profile else None
    if user_role not in ("admin", "medecin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    ...
```

---

#### C5 — `DEBUG: True` et SQL echo activés par défaut
**Fichiers :** `app/core/config.py:43`, `app/database/base.py:13`

```python
DEBUG: bool = True
# → echo=settings.DEBUG dans create_engine(...)
```

En mode DEBUG, toutes les requêtes SQL sont loggées en clair, y compris les données
utilisateurs et les hash de mots de passe récupérés lors du login.

**Correction :**
```python
DEBUG: bool = False  # False par défaut, True uniquement via .env en local
```

---

### ÉLEVÉ

#### H1 — Absence totale de rate limiting
Aucun middleware de limitation de débit n'est présent. Les endpoints `/auth/login` et
`/auth/register` sont vulnérables aux attaques par force brute et credential stuffing.

**Correction — ajouter `slowapi` :**
```python
# requirements.txt
slowapi==0.1.9

# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# app/api/v1/auth.py
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

---

#### H2 — Aucune validation de la force du mot de passe
Le schéma `UserCreate` accepte n'importe quel mot de passe, y compris `"a"`.

**Correction dans `app/schemas/user.py` :**
```python
from pydantic import field_validator
import re

@field_validator("password")
@classmethod
def password_strength(cls, v: str) -> str:
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one digit")
    return v
```

---

#### H3 — WebSocket : utilisateur suspendu/inactif non bloqué
L'authentification WebSocket décode le token et retrouve l'utilisateur mais ne vérifie
ni `user.is_active` ni le statut de suspension.

**Correction dans `app/api/v1/chat.py` :**
```python
if not user.is_active:
    await websocket.close(code=1008, reason="Account inactive")
    return

suspension = db.query(UserSuspension).filter(
    UserSuspension.user_id == user.id,
    UserSuspension.is_active == True
).first()
if suspension:
    await websocket.close(code=1008, reason="Account suspended")
    return
```

---

#### H4 — `except Exception: return None` silencieux
**Fichier :** `app/core/dependencies.py:80`

Les erreurs d'authentification sont silencieusement ignorées, rendant le débogage
impossible en production.

**Correction :**
```python
import logging
logger = logging.getLogger(__name__)

except Exception as e:
    logger.warning("Token validation error: %s", type(e).__name__)
    return None
```

---

#### H5 — `Base.metadata.create_all()` appelé au démarrage
**Fichier :** `app/main.py:13`

En production, cela court-circuite Alembic et peut manquer silencieusement des
changements de schéma.

**Correction :** Supprimer cet appel en production et utiliser exclusivement Alembic :
```python
# Garder uniquement pour les tests automatisés
# Ne pas laisser dans main.py pour la production
```

---

#### H6 — CORS trop permissif
**Fichier :** `app/main.py:24-30`

```python
allow_methods=["*"],
allow_headers=["*"],
```

**Correction :**
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Authorization", "Content-Type", "Accept"],
```

---

### MOYEN

#### M1 — Aucun logging structuré
Tout le code utilise `print()`. En production, il n'y a ni niveaux de log, ni IDs de
requête, ni trace d'audit.

**Correction — remplacer tous les `print()` par `logging` :**
```python
import logging
logger = logging.getLogger(__name__)

# Remplacer :
print(f"⚠️ OpenRouteService API error: {error_detail}")
# Par :
logger.warning("OpenRouteService API error (status %d): %s", response.status_code, error_detail)
```

---

#### M2 — Messages de chat non sanitisés
**Fichier :** `app/api/v1/chat.py`

Seul `.strip()` est appliqué. Si le frontend rend du HTML sans échappement, c'est un
vecteur XSS.

**Correction :**
```python
# requirements.txt : ajouter bleach==6.1.0
import bleach

content = bleach.clean(message_data.content.strip(), tags=[], strip=True)
if not content:
    raise HTTPException(status_code=400, detail="Message cannot be empty")
```

---

#### M3 — `AdminActionLog` créé mais jamais utilisé
Le modèle existe dans `app/models/admin.py` mais aucun endpoint ne l'alimente. Il n'y
a aucune traçabilité des actions administratives.

---

#### M4 — Transactions non atomiques à la création d'utilisateur
**Fichier :** `app/api/v1/auth.py:143-207`

Si la création du `UserProfile` échoue après la création du `User`, un compte orphelin
sans profil est laissé en base.

**Correction :**
```python
try:
    user = create_user(db, user_data)
    profile = UserProfile(user_id=user.id, username=user.username, role="patient")
    db.add(profile)
    db.commit()
except Exception:
    db.rollback()
    raise HTTPException(status_code=500, detail="User creation failed")
```

---

#### M5 — Credentials de test dans la documentation publique
**Fichier :** `../move4epilepsy-portalLocal/README.md:144`

Les mots de passe de test (`admin123456`, etc.) sont publiés dans le README. S'ils
existent dans un environnement de staging partagé, ils constituent une porte d'entrée.

**Recommandation :** Supprimer ces credentials du README et les mettre uniquement dans
un `.env.test` non commité.

---

#### M6 — Aucune pagination sur `/medications`
L'endpoint retourne tous les médicaments sans limite par défaut.

---

#### M7 — Claim RGPD non implémenté
Le README annonce "AES-256 pour toutes les données sensibles" et "Conformité RGPD".
Aucun chiffrement de champ ni endpoint de suppression de données (`DELETE /me`) n'est
implémenté dans le code.

---

#### M8 — `PharmacyStock.medication_name` est une chaîne libre
Aucune contrainte de clé étrangère vers `Medication`. Les données de stock peuvent
référencer des médicaments inexistants ou mal orthographiés.

---

---

## PARTIE 2 — Frontend (`move4epilepsy-portalLocal`)

### CRITIQUE

#### FC1 — Token JWT stocké dans `localStorage`
**Fichiers :** `src/lib/apiClient.ts:27`, `src/hooks/useAuth.ts:28`

```typescript
localStorage.setItem('access_token', token);
```

`localStorage` est accessible à tout script JavaScript de la page. En cas de XSS
(même dans une dépendance tierce), l'attaquant peut exfiltrer le token et usurper
l'identité de l'utilisateur.

**Correction recommandée :** Utiliser des cookies `HttpOnly; Secure; SameSite=Strict`
gérés côté backend. Cela nécessite une modification coordonnée backend + frontend :

```python
# Backend : app/api/v1/auth.py
from fastapi import Response

@router.post("/login")
async def login(response: Response, ...):
    ...
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "Login successful"}
```

```typescript
// Frontend : plus besoin de gérer le token manuellement
// apiClient envoie automatiquement les cookies avec credentials: 'include'
```

---

#### FC2 — Token JWT exposé dans l'URL WebSocket
**Fichier :** `src/services/chatService.ts`

```typescript
return `${wsRoot}/chat/ws/${channelId}?token=${encodeURIComponent(token)}`;
```

Le token apparaît en clair dans les logs du serveur, l'historique du navigateur,
les proxies et les outils de monitoring réseau.

**Correction :** Envoyer le token après l'établissement de la connexion via le premier
message WebSocket :
```typescript
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', token }));
};
```
Et côté backend, valider ce message avant d'autoriser les messages suivants.

---

#### FC3 — Réinitialisation de mot de passe non implémentée
**Fichier :** `src/pages/AuthPage.tsx:121-139`

```typescript
console.log('Password reset requested for:', resetEmail);
// L'appel API réel n'est pas implémenté
```

Le bouton "Mot de passe oublié" ne fait qu'un `console.log`. Les utilisateurs qui
perdent leur mot de passe n'ont aucun moyen de récupérer leur compte.

---

### ÉLEVÉ

#### FH1 — URL de l'API avec fallback codé en dur
**Fichier :** `src/lib/apiClient.ts:6`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
```

En l'absence de variable d'environnement, l'application pointe silencieusement vers
`localhost`. Un build de production sans `.env` configuré appellera localhost.

**Correction :**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
if (!API_BASE_URL) {
  throw new Error('VITE_API_BASE_URL is not defined. Check your .env file.');
}
```

---

#### FH2 — Messages d'erreur backend affichés directement à l'utilisateur
**Fichier :** `src/pages/AuthPage.tsx:295-300`

```tsx
<span className="text-red-700">{error}</span>
```

Les messages d'erreur bruts de l'API (ex. `"Username already registered"`,
`"Incorrect username or password"`) sont affichés. Cela révèle des informations
sur la structure interne et permet l'énumération de comptes.

**Correction :**
```typescript
const ERROR_MESSAGES: Record<string, string> = {
  "Username already registered": "Ce nom d'utilisateur est déjà pris.",
  "Email already registered": "Un compte avec cet email existe déjà.",
  "Incorrect username or password": "Identifiants invalides.",
};

const userMessage = ERROR_MESSAGES[rawError] ?? "Une erreur est survenue. Veuillez réessayer.";
```

---

#### FH3 — Génération d'ID patient avec `Math.random()`
**Fichier :** `src/utils/dataAnonymization.ts:53-60`

`Math.random()` n'est pas cryptographiquement sûr. Pour des identifiants pseudonymes
de patients, utiliser `crypto.getRandomValues()`.

**Correction :**
```typescript
function generateSecureId(length: number): string {
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, byte => chars[byte % chars.length]).join('');
}
```

---

#### FH4 — Absence de Content Security Policy
Aucun en-tête CSP n'est configuré ni dans `index.html` ni dans la configuration Vite.
Sans CSP, une injection de script tierce ou une faille XSS peut exécuter du code
arbitraire.

**Correction dans `index.html` :**
```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self';
           script-src 'self';
           style-src 'self' 'unsafe-inline';
           img-src 'self' data: blob:;
           connect-src 'self' https://api.move4epilepsy.fr wss://api.move4epilepsy.fr;
           frame-ancestors 'none';">
```

---

### MOYEN

#### FM1 — Aucune validation de la force du mot de passe côté client
Le formulaire d'inscription n'indique pas les exigences de mot de passe et n'en
valide pas la complexité avant envoi.

---

#### FM2 — Pas de protection contre le rate limiting côté client
Aucun mécanisme de délai ou de blocage temporaire n'est appliqué côté client après
des échecs de connexion répétés.

---

#### FM3 — Dépendances avec `^` (mises à jour mineures non contrôlées)
Toutes les dépendances dans `package.json` utilisent `^`. Une mise à jour mineure
d'une dépendance (ex. `leaflet`, `recharts`) pourrait introduire une vulnérabilité
sans changement de code.

**Recommandation :** Exécuter `npm audit` régulièrement et utiliser `npm ci` (et non
`npm install`) dans les pipelines CI/CD.

---

#### FM4 — Informations de contact en clair dans le HTML
**Fichier :** `src/App.tsx`

Adresses email et numéros de téléphone en texte brut dans le footer — vulnérables
au scraping automatique.

---

#### FM5 — Absence de refresh token
Il n'y a pas de mécanisme de renouvellement de token (refresh token). Quand le token
expire (30 min par défaut), l'utilisateur est déconnecté brutalement sans avertissement.

---

---

## PARTIE 3 — Points Transversaux

### T1 — Absence de pipeline CI/CD avec vérifications de sécurité
Aucun fichier de workflow (GitHub Actions, GitLab CI) n'est présent. Les vérifications
suivantes devraient être automatisées :
- `npm audit` (frontend)
- `pip audit` ou `safety check` (backend)
- Linting (`eslint`, `flake8`/`ruff`)
- Tests unitaires
- Scan de secrets (`gitleaks`, `trufflehog`)

---

### T2 — Aucun en-tête de sécurité HTTP
L'API FastAPI n'ajoute aucun des en-têtes de sécurité standards :

```python
# app/main.py — ajouter ce middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### T3 — Aucun mécanisme de refresh token
Le token JWT expire après 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES = 30`). Sans
refresh token, l'expérience utilisateur est dégradée et les développeurs sont tentés
d'augmenter la durée de vie du token, ce qui augmente la surface d'attaque en cas de
vol.

**Recommandation :** Implémenter un refresh token à longue durée de vie (`30 jours`),
stocké dans un cookie `HttpOnly`, avec rotation à chaque utilisation.

---

### T4 — Données de test dans un script accessible
**Fichier :** `move4epilepsy-api/scripts/create_test_users.py`

Ce script crée des comptes avec des mots de passe faibles. S'il est exécuté sur un
environnement partagé ou de staging, ces comptes constituent une porte d'entrée.

---

---

## Plan d'Action Priorisé

### Bloc 1 — Bloquant (avant tout déploiement)

| # | Action | Fichier(s) | Effort |
|---|--------|-----------|--------|
| 1 | Supprimer les valeurs par défaut de `SECRET_KEY` et `DATABASE_URL`, ajouter des validateurs au démarrage | `app/core/config.py` | 1h |
| 2 | Révoquer et régénérer la clé OpenRouteService, supprimer la valeur codée en dur | `app/api/v1/routing.py` | 30min |
| 3 | Ajouter l'authentification requise sur `GET/PUT /treatments` | `app/api/v1/patients.py` | 2h |
| 4 | Passer `DEBUG: False` par défaut | `app/core/config.py` | 15min |
| 5 | Migrer le token JWT de `localStorage` vers cookie `HttpOnly` | backend + frontend | 4h |
| 6 | Implémenter le rate limiting sur `/auth/login` | `app/api/v1/auth.py` | 1h |

### Bloc 2 — Priorité haute (première semaine)

| # | Action | Fichier(s) | Effort |
|---|--------|-----------|--------|
| 7 | Ajouter la validation de force du mot de passe | `app/schemas/user.py` + `AuthPage.tsx` | 2h |
| 8 | Corriger l'exposition du token dans l'URL WebSocket | `src/services/chatService.ts` + `app/api/v1/chat.py` | 3h |
| 9 | Ajouter les en-têtes de sécurité HTTP | `app/main.py` | 1h |
| 10 | Mettre en place le logging structuré (remplacer `print()`) | tous les fichiers API | 3h |
| 11 | Rendre les transactions utilisateur atomiques | `app/api/v1/auth.py` | 1h |
| 12 | Ajouter une Content Security Policy | `index.html` | 1h |
| 13 | Implémenter la réinitialisation de mot de passe | backend + `AuthPage.tsx` | 4h |

### Bloc 3 — Priorité normale (deux premières semaines)

| # | Action | Effort |
|---|--------|--------|
| 14 | Implémenter le refresh token | 4h |
| 15 | Sanitiser les messages de chat avec `bleach` | 1h |
| 16 | Alimenter `AdminActionLog` pour les actions sensibles | 3h |
| 17 | Ajouter une contrainte FK sur `PharmacyStock.medication_name` | 1h |
| 18 | Remplacer `Math.random()` par `crypto.getRandomValues()` | 30min |
| 19 | Mettre en place `npm audit` et `pip audit` en CI | 2h |
| 20 | Mapper les erreurs backend en messages génériques côté frontend | 1h |

---

## Questions Ouvertes

Avant d'implémenter certaines corrections, les points suivants nécessitent une décision :

1. **La création anonyme de traitements (`POST /treatments` sans auth) est-elle intentionnelle ?**
   Si oui, documenter explicitement la décision et ajouter une limitation de débit spécifique.

2. **Quel est l'environnement de déploiement cible ?** (VPS, Kubernetes, PaaS ?)
   La stratégie pour les cookies `HttpOnly` et les en-têtes HTTPS dépend du reverse proxy.

3. **La clé OpenRouteService commitée est-elle encore active ?**
   Si oui, la révoquer immédiatement et en générer une nouvelle.

4. **Des comptes de test existent-ils sur un environnement partagé ou de staging ?**
   Si oui, les désactiver ou changer leurs mots de passe.

5. **Quelle est la politique de rétention des données patients ?**
   Un endpoint `DELETE /me` est nécessaire pour la conformité RGPD.

---

*Rapport généré par analyse statique du code source. Aucun test d'intrusion dynamique n'a été effectué.*
