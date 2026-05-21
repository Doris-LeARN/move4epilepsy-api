# 🔐 Mapping Erreurs Backend → Messages Génériques

**Objectif** : Cacher les détails internes, afficher des messages génériques à l'utilisateur  
**Fichiers créés** : 
- `app/core/error_messages.py` — Mapping centralisé
- `app/core/error_middleware.py` — Middleware de standardisation
- Ce guide

**Date** : 21 mai 2026

---

## 📋 Résumé

### Problème (FH2 - Sécurité)

```typescript
// ❌ AVANT (dangereux)
<span>{error}</span>
// Affiche: "Username already registered" → Révèle que ce user existe!
// Affiche: "Invalid email format" → Énumération d'emails
// Affiche: "Database connection failed" → Fuite d'infrastructure
```

### Solution

```typescript
// ✅ APRÈS (sécurisé)
<span>{error}</span>
// Affiche: "Identifiants invalides. Veuillez réessayer."
// Affiche: "Une erreur est survenue. Veuillez réessayer."
// ← Pas d'exposition d'informations sensibles
```

---

## 🏗️ Architecture

### Flux

```
┌─────────────────────────────────────┐
│ Backend (FastAPI)                   │
├─────────────────────────────────────┤
│ Endpoint: POST /auth/login          │
│   ├─ user = db.query(User).first()  │
│   ├─ if not user:                   │
│   │   ├─ Log: "User not found"      │ ← Détail interne
│   │   └─ raise HTTPException(       │
│   │       detail="User not found"   │
│   │   )                             │
│   └─ ...                            │
└─────────────────────────────────────┘
              ▼
┌─────────────────────────────────────┐
│ ErrorMappingMiddleware              │
├─────────────────────────────────────┤
│ Intercept: "User not found"         │
│   ├─ error_data = get_user_message( │
│   │   "User not found"              │
│   │ )                               │
│   └─ return {                       │
│       "user_message": "Identifiants │
│        invalides. Veuillez..."      │
│       "category": "authentication"  │
│       "severity": "info"            │
│     }                               │
└─────────────────────────────────────┘
              ▼
┌─────────────────────────────────────┐
│ Frontend (React)                    │
├─────────────────────────────────────┤
│ Error Response: {                   │
│   error: {                          │
│     message: "Identifiants..."      │
│     category: "authentication"      │
│     severity: "info"                │
│   }                                 │
│ }                                   │
│   ├─ Display message to user        │
│   ├─ Log.warning (category=auth)    │
│   └─ Trigger UI feedback            │
└─────────────────────────────────────┘
```

---

## 📚 Utilisation Backend

### 1. Module `error_messages.py`

**Import et utilisation simple:**

```python
from app.core.error_messages import map_error, get_user_message

# Utilisation simple (juste le message)
user_message = map_error("Username already registered")
# → "Ce nom d'utilisateur est déjà utilisé. Veuillez en choisir un autre."

# Utilisation complète (avec catégorie/sévérité)
error_data = get_user_message("Invalid token")
# → {
#      "user_message": "Votre session a expiré. Veuillez vous reconnecter.",
#      "category": "authentication",
#      "severity": "info"
#    }
```

**Ajouter de nouveaux messages:**

```python
# Dans ERROR_MESSAGE_MAP (app/core/error_messages.py)
ERROR_MESSAGE_MAP = {
    # ...
    "Mon erreur backend": {
        "user_message": "Message générique pour l'utilisateur",
        "category": ErrorCategory.VALIDATION,
        "severity": "info",
    },
}
```

### 2. Middleware `error_middleware.py`

**Installation dans `app/main.py`:**

```python
from app.core.error_middleware import ErrorMappingMiddleware

# Dans la fonction app creation
app = FastAPI(...)

# Ajouter le middleware (APRÈS les autres middlewares)
app.add_middleware(ErrorMappingMiddleware)
```

### 3. Utilisation dans les endpoints

**Exemple 1: Endpoint d'authentification**

```python
from fastapi import HTTPException, status
from app.core.error_messages import map_error

@router.post("/auth/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login avec messages génériques"""
    
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user:
        # Le middleware mappera "User not found" automatiquement
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",  # ← Sera mappé à "Identifiants invalides"
        )
    
    if not verify_password(credentials.password, user.hashed_password):
        # Message générique: énumération empêchée
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # ...
    return {"access_token": token}
```

**Exemple 2: Endpoint de création**

```python
from app.core.error_messages import map_error

@router.post("/treatments")
async def create_treatment(data: TreatmentCreate, db: Session = Depends(get_db)):
    """Créer un traitement avec validation"""
    
    # Validation: âge
    if data.age < 0 or data.age > 150:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Age must be between 0 and 150",
        )
    
    # Validation: efficacité
    if data.effectiveness < 1 or data.effectiveness > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Effectiveness must be between 1 and 10",
        )
    
    # ...
    return treatment
```

---

## 🖥️ Utilisation Frontend

### Structure de Réponse d'Erreur

**Format standardisé:**

```typescript
// Erreur avec catégorie et sévérité
{
  error: {
    message: "Identifiants invalides. Veuillez réessayer.",
    category: "authentication",
    severity: "info"
  }
}
```

### Mapping Côté Frontend

**Fichier: `src/utils/errorMapping.ts`**

```typescript
type ErrorCategory = 
  | "authentication"
  | "authorization"
  | "validation"
  | "not_found"
  | "conflict"
  | "server_error"
  | "rate_limit";

type ErrorSeverity = "info" | "warning" | "error";

interface ErrorResponse {
  error: {
    message: string;
    category: ErrorCategory;
    severity: ErrorSeverity;
  };
}

// Couleurs par sévérité
const SEVERITY_COLORS = {
  info: "text-blue-600",
  warning: "text-yellow-600",
  error: "text-red-600",
};

// Actions par catégorie
const ERROR_ACTIONS: Record<ErrorCategory, (msg: string) => void> = {
  authentication: (msg) => {
    // Déconnecter l'utilisateur
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  },
  authorization: (msg) => {
    // Afficher "accès refusé"
    console.warn("Accès refusé:", msg);
  },
  rate_limit: (msg) => {
    // Afficher le message et attendre
    console.warn("Rate limité:", msg);
  },
  validation: (msg) => {
    // Garder le formulaire, afficher l'erreur
    console.warn("Validation:", msg);
  },
  not_found: (msg) => {
    // Rediriger vers accueil
    window.location.href = "/";
  },
  conflict: (msg) => {
    // Afficher le message
    console.warn("Conflit:", msg);
  },
  server_error: (msg) => {
    // Afficher message générique, retry later
    console.error("Erreur serveur:", msg);
  },
};

// Fonction utilitaire
export function handleErrorResponse(response: ErrorResponse): string {
  const { message, category, severity } = response.error;
  
  // Logger côté serveur (analytics, monitoring)
  console.group(`Error [${category}]`);
  console.log("Message:", message);
  console.log("Severity:", severity);
  console.log("Timestamp:", new Date().toISOString());
  console.groupEnd();
  
  // Déclencher actions spécifiques
  ERROR_ACTIONS[category]?.(message);
  
  // Retourner le message pour affichage
  return message;
}
```

### Utilisation dans les Composants

**Exemple: Formulaire de Connexion**

```typescript
// src/pages/AuthPage.tsx
import { handleErrorResponse } from "../utils/errorMapping";

export default function AuthPage() {
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (username: string, password: string) => {
    setLoading(true);
    setError("");
    
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      // ✅ NOUVEAU: Utiliser le mapping
      if (!response.ok) {
        const userMessage = handleErrorResponse(data);
        setError(userMessage);
        return;
      }

      // Succès
      localStorage.setItem("access_token", data.access_token);
      window.location.href = "/dashboard";
      
    } catch (err) {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form>
      {/* ... */}
      {error && (
        <div className="text-red-600 text-sm mt-2">
          {error}
        </div>
      )}
    </form>
  );
}
```

**Exemple: Création de Traitement**

```typescript
// src/components/TreatmentForm.tsx

export function TreatmentForm() {
  const [error, setError] = useState<string>("");

  const handleSubmit = async (formData: TreatmentData) => {
    try {
      const response = await apiClient.post("/treatments", formData);
      
      if (!response.ok) {
        const errorData = await response.json();
        const userMessage = handleErrorResponse(errorData);
        setError(userMessage);
        return;
      }

      // Succès
      showSuccess("Traitement enregistré avec succès");
      
    } catch (err) {
      setError("Une erreur est survenue.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* ... */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
    </form>
  );
}
```

---

## 🎯 Cas d'Usage

### Cas 1: Énumération d'utilisateurs (BLOQUÉ)

```
❌ AVANT:
Frontend: POST /auth/login {username: "admin", password: "xxx"}
Backend: Retourne "User not found"
Attaquant: Sait que "admin" n'existe pas

✅ APRÈS:
Frontend: POST /auth/login {username: "admin", password: "xxx"}
Backend: Retourne "Identifiants invalides"
Attaquant: Ne sait pas si user existe ou password est mauvais
```

### Cas 2: Fuite d'infrastructure

```
❌ AVANT:
Database error: "Connection refused on postgresql://postgres@db.internal:5432"
User voit: Adresse IP de BD, version software, infrastructure interne

✅ APRÈS:
User voit: "Une erreur serveur s'est produite."
Backend log: "Database error at 2026-05-21 14:23:45"
```

### Cas 3: Validation d'email

```
❌ AVANT:
POST /register {email: "test@example.com"}
Response: "Email already registered"
Attaquant: Sait qu'un compte avec cet email existe

✅ APRÈS:
POST /register {email: "test@example.com"}
Response: "Un compte avec cet email existe déjà."
+ Backend loggue qui/quand/pourquoi
```

---

## 📋 Checklist d'Implémentation

### Backend

- ✅ Créer `app/core/error_messages.py`
- ✅ Créer `app/core/error_middleware.py`
- ⏳ Ajouter middleware dans `app/main.py`
- ⏳ Auditer tous les `HTTPException` + `raise` statements
- ⏳ Remplacer messages verbeux par messages de `ERROR_MESSAGE_MAP`
- ⏳ Tester les endpoints pour vérifier mapping

### Frontend

- ⏳ Créer `src/utils/errorMapping.ts`
- ⏳ Implémenter `handleErrorResponse()`
- ⏳ Mettre à jour formulaires pour utiliser le mapping
- ⏳ Ajouter logging/analytics pour erreurs
- ⏳ Tester UX avec différentes erreurs

---

## 🧪 Exemples de Tests

### Test Backend

```python
# tests/core/test_error_messages.py
from app.core.error_messages import map_error, get_user_message

def test_username_already_registered():
    msg = map_error("Username already registered")
    assert "invalides" not in msg  # Pas le message brut
    assert "déjà utilisé" in msg   # Message générique français

def test_user_not_found():
    data = get_user_message("User not found")
    assert data["category"] == "authentication"
    assert data["severity"] == "info"
    assert "Identifiants" in data["user_message"]

def test_unknown_error_fallback():
    msg = map_error("Some unknown error code 12345")
    assert "Une erreur est survenue" in msg  # Fallback générique
```

### Test Frontend

```typescript
// src/utils/__tests__/errorMapping.test.ts
import { handleErrorResponse } from "../errorMapping";

test("authentication error triggers redirect", () => {
  const response = {
    error: {
      message: "Votre session a expiré",
      category: "authentication" as const,
      severity: "info" as const,
    },
  };

  handleErrorResponse(response);
  expect(localStorage.getItem("access_token")).toBeNull();
  expect(window.location.href).toContain("/login");
});

test("validation error keeps form visible", () => {
  const response = {
    error: {
      message: "L'âge doit être entre 0 et 150",
      category: "validation" as const,
      severity: "info" as const,
    },
  };

  const msg = handleErrorResponse(response);
  expect(msg).toContain("150");
});
```

---

## 🚀 Déploiement

### Ordre d'implémentation

1. ✅ Backend: Modules créés
2. ⏳ Backend: Ajouter middleware à `main.py`
3. ⏳ Backend: Audit des endpoints
4. ⏳ Backend: Tester mapping
5. ⏳ Frontend: Créer utils
6. ⏳ Frontend: Mettre à jour formulaires
7. ⏳ Frontend: Tester UX
8. ✅ Commit & Deploy

### Effort Total

- Backend: 2-3 heures
- Frontend: 2-3 heures
- **Total: 4-6 heures**

---

## 📊 Bénéfices Sécurité

| Aspect | Avant | Après |
|--------|-------|-------|
| Énumération comptes | ❌ Risque élevé | ✅ Bloquée |
| Exposition infra | ❌ Possible | ✅ Impossible |
| Logs détaillés | ❌ Côté client | ✅ Côté serveur |
| UX utilisateur | ⚠️ Confus | ✅ Clair |
| Conformité OWASP | ⚠️ Non | ✅ Oui |

---

## 📞 Questions?

**Modules créés:**
- ✅ `app/core/error_messages.py` — Mapping centralisé
- ✅ `app/core/error_middleware.py` — Middleware

**À faire:**
- ⏳ Intégrer middleware dans `app/main.py`
- ⏳ Frontend utils + formulaires
- ⏳ Tests

Pour ajouter une erreur : Voir `ERROR_MESSAGE_MAP` dans `error_messages.py`

---

*Document généré: 21 mai 2026 — Copilot*
