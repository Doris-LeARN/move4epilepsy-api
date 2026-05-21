# ✅ Bloc 1 — Items #1 & #2 Complétés

**Date:** 21 mai 2026  
**Status:** ✅ COMPLÉTÉ  
**Sévérité:** 🔴 CRITIQUE (Secrets exposés)

---

## 📋 Changements Implémentés

### Item #1: SECRET_KEY & DATABASE_URL Validators ✅

**Fichier:** `app/core/config.py`

#### AVANT:
```python
SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/move4epilepsy")
# ❌ Pas de validation → risque de déployer avec des credentials par défaut
```

#### APRÈS:
```python
SECRET_KEY: str = Field(default="")
DATABASE_URL: str = Field(default="")

@field_validator("SECRET_KEY")
@classmethod
def secret_key_must_be_set(cls, v: str) -> str:
    """SECRET_KEY doit être explicitement configuré via .env"""
    if not v or v == "change-me-in-production-use-env-variable":
        raise ValueError(
            "🔴 ERREUR CRITIQUE: SECRET_KEY must be explicitly set via environment variable (.env). "
            "Ne pas committer la valeur par défaut!"
        )
    if len(v) < 32:
        raise ValueError(
            "🔴 ERREUR: SECRET_KEY must be at least 32 characters for security"
        )
    return v

@field_validator("DATABASE_URL")
@classmethod
def database_url_must_be_set(cls, v: str) -> str:
    """DATABASE_URL doit être explicitement configuré via .env"""
    if not v or v == "postgresql://postgres:postgres@localhost:5432/move4epilepsy":
        raise ValueError(
            "🔴 ERREUR CRITIQUE: DATABASE_URL must be explicitly set via environment variable (.env). "
            "Never commit default credentials!"
        )
    if not v.startswith(("postgresql://", "postgres://")):
        raise ValueError(
            "🔴 ERREUR: DATABASE_URL must start with postgresql:// or postgres://"
        )
    return v
```

**Impact:**
- ✅ Le démarrage de l'API ÉCHOUE si `SECRET_KEY` ou `DATABASE_URL` ne sont pas configurés
- ✅ Message d'erreur clair pour guider le développeur
- ✅ Longueur minimale de 32 caractères pour SECRET_KEY
- ✅ Format validation pour DATABASE_URL

---

### Item #2: Clé OpenRouteService Supprimée ✅

**Fichier:** `app/api/v1/routing.py`

#### AVANT:
```python
OPENROUTESERVICE_API_KEY = os.getenv(
    "OPENROUTESERVICE_API_KEY",
    "5b3ce3597851110001cf6248e8c8e8c8b8c8e8c8b8c8e8c8b8c8e8c8b"  # ❌ EXPOSÉE!
)
# Cette clé était visible dans le code source
```

#### APRÈS:
```python
# Clé API OpenRouteService depuis les variables d'environnement
# ⚠️ CRITIQUE: Ne JAMAIS utiliser de valeur par défaut exposée
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")

if not OPENROUTESERVICE_API_KEY:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "⚠️ OPENROUTESERVICE_API_KEY not set. Routing will use Haversine fallback only. "
        "Set OPENROUTESERVICE_API_KEY in .env for full routing capabilities."
    )

# ... plus tard dans le code ...
if httpx is not None and OPENROUTESERVICE_API_KEY:  # ✅ Vérification avant utilisation
    # Utiliser OpenRouteService
else:
    # Fallback: Haversine
```

**Impact:**
- ✅ Aucune clé exposée dans le code source
- ✅ Mode dégradé (Haversine fallback) si la clé n'est pas configurée
- ✅ Warning en logs si la clé manque (pour alerter le développeur)

---

## 🧪 Test d'Erreurs

### Cas 1: Démarrage SANS .env

```bash
$ python -m app.main
Traceback (most recent call last):
  ...
ValueError: 🔴 ERREUR CRITIQUE: SECRET_KEY must be explicitly set via environment variable (.env). Ne pas committer la valeur par défaut!
```

✅ **Comportement attendu:** L'API refuse de démarrer

### Cas 2: Démarrage AVEC .env valide

```bash
$ echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
$ echo "DATABASE_URL=postgresql://user:pass@db.example.com:5432/move4epilepsy" >> .env
$ python -m app.main

INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **Comportement attendu:** L'API démarre normalement

### Cas 3: OpenRouteService sans clé

```bash
# Pas de OPENROUTESERVICE_API_KEY dans .env
$ curl "http://localhost:8000/api/v1/routing/directions/driving-car?start=2.3522,48.8566&end=2.3963,48.8566"

{
  "distance": 4.2,
  "duration": 15
}
# ✅ Fallback à Haversine, pas d'erreur
```

---

## 🔐 Sécurité: Avant vs Après

| Aspect | AVANT ❌ | APRÈS ✅ |
|--------|---------|---------|
| **SECRET_KEY exposée** | Oui (par défaut) | Non (validation obligatoire) |
| **DATABASE_URL exposée** | Oui (credentials postgres) | Non (validation obligatoire) |
| **OpenRouteService clé** | Oui (dans le code source) | Non (env variable uniquement) |
| **Validation au démarrage** | Non | Oui (lève erreur) |
| **Mode dégradé** | N/A | Oui (Haversine fallback) |
| **Messages d'erreur** | Non | Oui (aide au dépannage) |

---

## 📋 Checklist Déploiement

- [ ] Générer SECRET_KEY: `openssl rand -hex 32`
- [ ] Configurer DATABASE_URL dans `.env`
- [ ] Configurer OPENROUTESERVICE_API_KEY dans `.env` (optionnel, fallback disponible)
- [ ] Valider que `.env` est dans `.gitignore` (ne pas committer!)
- [ ] Tester le démarrage: `python -m app.main`
- [ ] Vérifier les logs pour les warnings (ex: missing API key)
- [ ] Tester l'endpoint de routing: `curl http://localhost:8000/api/v1/routing/directions/driving-car?start=...`

---

## 🚀 Bloc 1 — Statut Actuel

| # | Action | Status |
|---|--------|--------|
| 1 | SECRET_KEY / DATABASE_URL validators | ✅ **DONE** |
| 2 | Clé OpenRouteService supprimée | ✅ **DONE** |
| 3 | Auth sur GET/PUT /treatments | ✅ **DONE** |
| 4 | DEBUG: False | ✅ **DONE** |
| 5 | JWT HttpOnly cookies | ✅ **DONE** (backend) |
| 6 | Rate limiting /login | ✅ **DONE** |

---

## ⚠️ REMARQUES IMPORTANTES

### Ancienne clé OpenRouteService

La clé exposée dans le code source était:
```
5b3ce3597851110001cf6248e8c8e8c8b8c8e8c8b8c8e8c8b8c8e8c8b
```

**Actions recommandées:**
1. ✅ Déjà supprimée du code
2. 🔄 **À FAIRE:** Révoquer cette clé sur https://openrouteservice.org
3. 🔄 **À FAIRE:** Générer une nouvelle clé
4. 🔄 **À FAIRE:** Configurer dans `.env`

---

## 📚 Références

- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP: Secrets Management](https://owasp.org/www-community/attacks/Secrets_Management)
