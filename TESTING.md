## Base PostgreSQL de test

Les tests utilisent une vraie base PostgreSQL dédiée afin de supporter les types
`ARRAY`, `JSONB` et les contraintes SQL utilisées par l'API.

```bash
docker compose -f docker-compose.test.yml up -d
source .venv/bin/activate
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/move4epilepsy_test \
  pytest
```

Ne configurez jamais `TEST_DATABASE_URL` avec l'URL de développement ou de
production. Les fixtures nettoient les tables de la base de test après chaque test.

# 🧪 Tests Unitaires - Move4Epilepsy API

Guide complet pour exécuter et écrire les tests.

---

## 📁 Structure

```
tests/
├── conftest.py              # Fixtures pytest globales
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── test_auth.py         # Tests authentification
│   └── test_patients.py     # Tests patients/traitements
├── core/
│   ├── __init__.py
│   ├── test_security.py     # Tests sécurité & headers
│   └── test_validation.py   # Tests validateurs
└── models/
    └── __init__.py
```

---

## 🚀 Démarrage Rapide

### Installer les dépendances (déjà fait)

```bash
.venv/bin/pip install pytest pytest-asyncio pytest-cov
```

### Lancer tous les tests

```bash
# Avec .venv
.venv/bin/pytest

# Ou avec python directement
python -m pytest
```

### Lancer des tests spécifiques

```bash
# Tous les tests auth
pytest tests/api/test_auth.py

# Un test spécifique
pytest tests/api/test_auth.py::TestAuthRegister::test_register_success

# Tests avec pattern
pytest tests/ -k "register"

# Tests avec markers
pytest -m security
```

### Voir la couverture de code

```bash
# Avec rapport terminal
pytest --cov=app --cov-report=term-missing

# Avec rapport HTML (ouvre dans navigateur)
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 📊 Commandes Utiles

### Exécution rapide

```bash
# Verbose mode
pytest -v

# Très verbose (affiche les prints)
pytest -vv

# Arrêter au premier erreur
pytest -x

# Arrêter après N erreurs
pytest --maxfail=2

# Pas de capture de output (voir les prints)
pytest -s
```

### Filtrer tests

```bash
# Par nom de test
pytest -k "test_login"

# Par module
pytest tests/api/test_auth.py

# Par classe
pytest tests/api/test_auth.py::TestAuthLogin

# Par marker
pytest -m security

# Exclure markers
pytest -m "not slow"
```

### Profiling

```bash
# Montrer les 10 tests les plus lents
pytest --durations=10

# Profile de test
pytest --profile
```

---

## ✍️ Écrire des Tests

### Structure d'un test

```python
def test_something(client):
    """Docstring descriptive"""
    # Arrange
    data = {"key": "value"}
    
    # Act
    response = client.post("/api/v1/endpoint", json=data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

### Fixtures disponibles

| Fixture | Description |
|---------|------------|
| `client` | Client FastAPI test (with DB) |
| `db_session` | Session DB pour tests |
| `test_user` | User de test (patient) |
| `test_admin` | User admin de test |
| `auth_headers` | Headers JWT d'authentification (user) |
| `admin_auth_headers` | Headers JWT admin |

### Exemple complet

```python
def test_create_with_auth(client, auth_headers):
    """Test création avec authentification"""
    response = client.post(
        "/api/v1/endpoint",
        json={"field": "value"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "value"
```

---

## 🧩 Markers Personnalisés

```python
import pytest

# Marquer un test
@pytest.mark.security
def test_something():
    pass

# Marquer une classe
@pytest.mark.slow
class TestSomething:
    pass

# Exécuter par marker
pytest -m security
```

### Markers disponibles

- `@pytest.mark.security` - Tests de sécurité
- `@pytest.mark.slow` - Tests lents
- `@pytest.mark.integration` - Tests d'intégration
- `@pytest.mark.unit` - Tests unitaires

---

## 📈 Coverage

### Voir la couverture

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# JSON report (pour CI/CD)
pytest --cov=app --cov-report=json
```

### Objectifs de couverture

- **Minimum** : 70%
- **Recommandé** : 85%
- **Excellent** : 95%+

---

## 🔄 Exécution avec .venv

### Depuis le repo root

```bash
# Lancer tous les tests
.venv/bin/pytest

# Lancer avec options
.venv/bin/pytest -v --cov=app

# Lancer un fichier spécifique
.venv/bin/pytest tests/api/test_auth.py
```

### Ou activer le venv d'abord

```bash
source .venv/bin/activate
pytest
deactivate
```

---

## 📝 Tests Disponibles

### API Tests (`tests/api/`)

**test_auth.py** (30+ tests)
- Register (succès, duplicate username, duplicate email, invalid email)
- Login (succès, mauvais password, user inexistant, user inactif)
- Get me (authentifié, pas de token, token invalide)
- Get profile

**test_patients.py** (20+ tests)
- Create treatment (anonyme, avec durée, validations)
- List treatments (vide, avec filtres)
- Get stats (vide, avec données)

### Core Tests (`tests/core/`)

**test_security.py** (15+ tests)
- Security headers (nosniff, X-Frame, XSS, HSTS, CSP)
- CORS protection
- Health endpoint
- Input validation stricte
- Authentication & authorization
- Admin endpoints

**test_validation.py** (30+ tests)
- Username validation
- Email validation
- Safe string validation
- Age bounds (0-150)
- Effectiveness bounds (1-10)
- Positive integers

---

## 🐛 Debugging

### Mode debug

```bash
# Avec pdb breakpoints
pytest --pdb

# Arrêt au premier erreur
pytest -x --pdb
```

### Voir les logs

```bash
# Sans capture
pytest -s

# Avec logs
pytest -v -s
```

### Inspecter une fixture

```python
def test_something(client, db_session):
    print(f"Client: {client}")
    print(f"DB session: {db_session}")
    print(f"DB tables: {db_session.query(...)}")
```

---

## 🚀 CI/CD Integration

### GitHub Actions (exemple)

```yaml
- name: Run tests
  run: |
    .venv/bin/pip install -q pytest pytest-asyncio pytest-cov
    .venv/bin/pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### GitLab CI (exemple)

```yaml
test:
  script:
    - .venv/bin/pytest --cov=app
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## 📚 Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-events/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_basics.html)

---

**Besoin d'aide ?** → Voir `.venv/bin/pytest --help`
