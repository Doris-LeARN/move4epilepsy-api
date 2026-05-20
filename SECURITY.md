# 🔐 SÉCURITÉ - Move4Epilepsy API

Documentation complète des mesures de sécurité implémentées.

---

## 1. Authentification & Tokens JWT

### ✅ Implémentation

- **Algorithme** : HS256 (HMAC-SHA256)
- **Expiration** : 30 minutes par défaut
- **Hachage des passwords** : bcrypt avec salt aléatoire
- **Validation stricte** : Tokens validés sur chaque requête protégée

### ⚠️ Production Requirements

```env
# OBLIGATOIRE - Générer une clé forte:
python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=<clé_générée>
ENVIRONMENT=production
DEBUG=False
```

---

## 2. Endurance contre les Attaques

### Rate Limiting
- **Auth endpoints** : 5 requêtes/minute (brute-force protection)
- **API générales** : 100 requêtes/minute
- **Endpoints publics** : 200 requêtes/minute
- **Réponse** : 429 Too Many Requests

### Headers de Sécurité HTTP

| Header | Valeur | Raison |
|--------|--------|--------|
| `X-Content-Type-Options` | `nosniff` | Prévient MIME-sniffing attacks |
| `X-Frame-Options` | `DENY` | Prévient clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Prévient XSS (navigateurs anciens) |
| `Strict-Transport-Security` | `max-age=31536000` | Force HTTPS (1 an) |
| `Content-Security-Policy` | `default-src 'self'` | Restrict resources origin |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer info |
| `Permissions-Policy` | Geolocation/Microphone disabled | Restrict browser features |

### CORS Protection
- **Whitelist stricte** : Seulement origins autorisés via `.env`
- **Credentials** : `allow_credentials=True` seulement si confiance
- **Methods** : Seulement GET, POST, PUT, DELETE (pas de *)
- **Headers** : Seulement Content-Type, Authorization (pas de *)
- **Max-Age** : 3600 secondes

### Trusted Host Middleware
- Valide que les requests viennent de hosts autorisés
- Prévient Host Header Injection

---

## 3. Validation des Inputs

### Stricte Validation Pydantic

```python
# Username: alphanumérique + - _ . seulement (3-50 chars)
# Email: format RFC 5322 (max 254 chars)
# Age: 0-150 seulement
# Effectiveness: 1-10 seulement
```

**Fichier** : `app/core/validation.py`

### Protection SQL Injection
- **SQLAlchemy ORM** : Parameterized queries automatiquement
- **Pas de raw SQL** : Éviter `db.execute(raw_sql)`
- **Type Safety** : Pydantic valide les types avant DB

---

## 4. Stockage Sécurisé des Credentials

### ✅ Passwords
```python
# Hash bcrypt (72 bytes limit)
from app.core.security import get_password_hash, verify_password

hashed = get_password_hash("user_password")
is_valid = verify_password("user_input", hashed)
```

### ✅ JWT Tokens
- Stockés en mémoire (pas de cookies sauf si HTTPS)
- Envoyés via `Authorization: Bearer <token>` header
- Validés sur chaque requête

### ⚠️ Configuration
```env
# NE JAMAIS commiter en clair
SECRET_KEY=<strong_key>        # .gitignore
DATABASE_URL=<db_url>          # .gitignore
```

---

## 5. Design Anonyme (Intentionnel)

### Endpoint `/patients/treatments` (NON protégé)
- **Raison** : Collecte participative anonyme de données cliniques
- **Bénéfice** : Pas d'authentification = taux participation ↑
- **Risque mitigation** : Rate limiting 200/min + input validation

### Données Sensibles
- Patient `name` = optionnel/pseudonyme
- No email required
- Age/sexe/localisation seulement
- Anonymat préservé

---

## 6. Logging & Audit

### Logging
- **Tous les endpoints** : Méthode + path + status
- **Authentification** : Success/failures
- **Rate limits exceeded** : IP logging
- **Level** : Configurable via `LOG_LEVEL` env

### Fichiers
```
logs/
├── app.log          # Application logs
└── audit.log        # Audit trail (future)
```

### Production Requirement
```env
LOG_LEVEL=WARNING
LOG_DIR=/var/log/move4epilepsy/
```

---

## 7. Base de Données

### PostgreSQL Security
- **User séparé** : Pas de `postgres` en production
- **Permissions limitées** : Row-level security (RLS) possible
- **Connexion SSL** : Via `sslmode=require` en production
- **Backups chiffrés** : Outside docker volumes

### Migrations Alembic
- Versionner les schémas
- Audit trail de changements
- Rollback capability

### Docker Security
```yaml
db:
  image: postgres:16-alpine  # Slim image
  # PASSWORD STRONG via env
  environment:
    POSTGRES_PASSWORD: ${DB_PASSWORD}  # Never hardcoded
```

---

## 8. Déploiement Production Checklist

### ✅ Pré-déploiement
- [ ] `DEBUG=False` OBLIGATOIRE
- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` généré & stocké sécurisé
- [ ] `DATABASE_URL` pointe BD production
- [ ] `FORCE_HTTPS=True`
- [ ] `BACKEND_CORS_ORIGINS` = exact domains (pas *)
- [ ] `.env` NOT in git (`.gitignore`)
- [ ] `LOG_LEVEL=WARNING` ou `ERROR`
- [ ] HTTPS/SSL certificate configuré

### ✅ Infrastructure
- [ ] Reverse proxy (nginx) en front de FastAPI
- [ ] SSL/TLS certificate (Let's Encrypt)
- [ ] Firewall: seulement ports 80/443
- [ ] Database: separate secure subnet
- [ ] Backups: hors du container
- [ ] Monitoring: uptime/logs centralisés

### ✅ Runtime
- [ ] Health checks actifs
- [ ] Rate limiting actif
- [ ] Logging centralisé
- [ ] Updates de sécurité reguliers

---

## 9. Dépendances de Sécurité

| Package | Raison |
|---------|--------|
| `bcrypt` | Password hashing secure |
| `python-jose` | JWT implementation |
| `slowapi` | Rate limiting |
| `pydantic` | Input validation |
| `sqlalchemy` | ORM (parameterized queries) |

### Mise à jour
```bash
# Vérifier vulnerabilities
pip-audit

# Update
pip install --upgrade -r requirements.txt
```

---

## 10. Contacts & Responsabilités

**Security Issues** : Ne PAS créer de GitHub Issues publiques
1. Envoyer email : security@move4epilepsy.com
2. Inclure : Description + CVE (si applicable) + proof-of-concept
3. Allow 48h response time

---

## Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
