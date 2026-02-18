# 🔄 Changements Frontend pour Migration Supabase → FastAPI

## 📋 Résumé des Changements

### ✅ Déjà Fait (Fichiers `.api.ts` existants)
- `apiClient.ts` - Client HTTP pour FastAPI ✅
- `authService.api.ts` - Service auth FastAPI ✅
- `medicationService.api.ts` - Service médicaments FastAPI ✅
- `pharmacyService.api.ts` - Service pharmacies FastAPI ✅
- `patientService.api.ts` - Service patients FastAPI ✅

### ⚠️ À Changer (Utilise encore Supabase)

## 1. 🔐 Authentification (`useAuth.ts`)

**Fichier**: `src/hooks/useAuth.ts`

**Problème**: Utilise encore `supabase.auth.getSession()` et `supabase.auth.onAuthStateChange()`

**Changements nécessaires**:

```typescript
// ❌ AVANT (Supabase)
import { supabase } from '../lib/supabase';
const { data: { session } } = await supabase.auth.getSession();
supabase.auth.onAuthStateChange(...)

// ✅ APRÈS (FastAPI)
import { apiClient } from '../lib/apiClient';
import { authService } from '../services/authService.api';

// Remplacer getSession() par vérification du token
const token = localStorage.getItem('access_token');
if (token) {
  try {
    const user = await apiClient.get('/auth/me');
    await updateAuthState(user);
  } catch {
    // Token invalide, déconnecter
    apiClient.setAccessToken(null);
  }
}

// Remplacer onAuthStateChange par un système de polling ou événements custom
// (FastAPI n'a pas de real-time comme Supabase)
```

**Impact**: 
- ❌ Plus de real-time auth (pas de `onAuthStateChange`)
- ✅ Solution: Vérifier le token au chargement + écouter les actions login/logout

---

## 2. 📝 Services qui utilisent encore Supabase directement

**Fichiers à migrer**:

### `src/services/patientService.ts`
- ❌ Utilise `supabase.from('patient_treatments')`
- ✅ Remplacer par `apiClient.post('/patients/treatments')`

### `src/services/medicationService.ts` (si existe)
- ❌ Utilise `supabase.from('medications')`
- ✅ Utiliser `medicationService.api.ts` à la place

### `src/services/pharmacyService.ts` (si existe)
- ❌ Utilise `supabase.from('pharmacies')`
- ✅ Utiliser `pharmacyService.api.ts` à la place

### `src/services/authService.ts` (si existe)
- ❌ Utilise `supabase.auth.signUp()`, `supabase.auth.signIn()`
- ✅ Utiliser `authService.api.ts` à la place

---

## 3. 🔧 Variables d'Environnement (`.env`)

**Fichier**: `.env`

**Changements**:

```bash
# ❌ AVANT (Supabase)
VITE_SUPABASE_URL=https://mmtqcpillfoildqtildi.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...

# ✅ APRÈS (FastAPI)
VITE_API_BASE_URL=http://localhost:8000/api/v1
# Plus besoin de VITE_SUPABASE_URL ni VITE_SUPABASE_ANON_KEY
```

---

## 4. 📦 Imports à Remplacer

**Rechercher et remplacer dans tout le projet**:

```typescript
// ❌ AVANT
import { supabase } from '../lib/supabase';
import { authService } from '../services/authService';
import { medicationService } from '../services/medicationService';
import { pharmacyService } from '../services/pharmacyService';
import { patientService } from '../services/patientService';

// ✅ APRÈS
import { apiClient } from '../lib/apiClient';
import { authService } from '../services/authService.api';
import { medicationService } from '../services/medicationService.api';
import { pharmacyService } from '../services/pharmacyService.api';
import { patientService } from '../services/patientService.api';
```

---

## 5. 🔄 Différences Clés Supabase vs FastAPI

| Fonctionnalité | Supabase | FastAPI | Solution |
|----------------|----------|---------|----------|
| **Auth Real-time** | `onAuthStateChange()` | ❌ Pas de real-time | Vérifier token au chargement + écouter login/logout |
| **Queries** | `.from('table').select()` | `GET /api/v1/table` | Utiliser `apiClient.get()` |
| **Insert** | `.insert(data)` | `POST /api/v1/table` | Utiliser `apiClient.post()` |
| **Update** | `.update(data).eq('id', id)` | `PUT /api/v1/table/{id}` | Utiliser `apiClient.put()` |
| **Delete** | `.delete().eq('id', id)` | `DELETE /api/v1/table/{id}` | Utiliser `apiClient.delete()` |
| **Filtres** | `.eq('field', value)` | Query params `?field=value` | Passer dans l'URL ou body |
| **Pagination** | `.range(start, end)` | Query params `?skip=0&limit=10` | Passer dans l'URL |
| **Real-time** | `.on('*', callback)` | ❌ Pas de real-time | WebSockets ou polling si nécessaire |

---

## 6. 🎯 Checklist de Migration

### Étape 1: Configuration
- [ ] Mettre à jour `.env` avec `VITE_API_BASE_URL`
- [ ] Supprimer `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY`

### Étape 2: Authentification
- [ ] Migrer `useAuth.ts` pour utiliser `authService.api.ts`
- [ ] Remplacer `supabase.auth.getSession()` par vérification token
- [ ] Remplacer `supabase.auth.onAuthStateChange()` par système custom
- [ ] Tester login/logout

### Étape 3: Services
- [ ] Vérifier que tous les services utilisent les versions `.api.ts`
- [ ] Migrer `patientService.ts` vers `patientService.api.ts`
- [ ] Remplacer tous les appels `supabase.from()` par `apiClient`

### Étape 4: Composants
- [ ] Chercher tous les imports de `supabase`
- [ ] Remplacer par `apiClient` ou services `.api.ts`
- [ ] Tester chaque page/composant

### Étape 5: Tests
- [ ] Tester l'authentification complète
- [ ] Tester toutes les pages principales
- [ ] Vérifier les erreurs réseau (CORS, 401, 404, etc.)

---

## 7. 🐛 Problèmes Courants

### CORS
**Erreur**: `Access-Control-Allow-Origin`
**Solution**: Vérifier `BACKEND_CORS_ORIGINS` dans `.env` de l'API

### 401 Unauthorized
**Erreur**: Token manquant ou invalide
**Solution**: Vérifier que le token est envoyé dans le header `Authorization: Bearer <token>`

### Format de données différent
**Erreur**: Les réponses FastAPI peuvent avoir un format différent de Supabase
**Solution**: Adapter les interfaces TypeScript et les mappers de données

### Real-time manquant
**Problème**: Pas de mise à jour automatique comme Supabase
**Solution**: Implémenter polling ou WebSockets si nécessaire

---

## 8. 📚 Ressources

- **API FastAPI**: http://localhost:8000/docs (Swagger)
- **Client API**: `src/lib/apiClient.ts`
- **Services API**: `src/services/*.api.ts`

---

**✅ Résumé**: Le frontend est déjà à 80% prêt ! Il faut principalement migrer `useAuth.ts` et remplacer les appels directs à Supabase par les services `.api.ts`.
