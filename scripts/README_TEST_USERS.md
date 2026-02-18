# 👥 Création d'Utilisateurs Tests

## 🚀 Méthode Recommandée : Script Python

Le script `create_test_users.py` est la méthode la plus simple et sécurisée pour créer des utilisateurs de test.

### Utilisation

```bash
cd move4epilepsy-api
source venv/bin/activate  # Si vous utilisez un venv
python scripts/create_test_users.py
```

### Utilisateurs créés

Le script crée automatiquement 4 utilisateurs de test :

| Username | Password | Rôle | Email |
|----------|----------|------|-------|
| `admin_test` | `admin123456` | admin | admin@test.com |
| `pharmacien_test` | `pharmacien123456` | pharmacien | pharmacien@test.com |
| `medecin_test` | `medecin123456` | medecin | medecin@test.com |
| `patient_test` | `patient123456` | patient | patient@test.com |

### Fonctionnalités

- ✅ Vérifie si les utilisateurs existent déjà (évite les doublons)
- ✅ Crée les utilisateurs avec leurs profils complets
- ✅ Affiche un résumé détaillé
- ✅ Gère les erreurs proprement
- ✅ Affiche les informations de connexion

### Exemple de sortie

```
🔐 Création des utilisateurs de test...

✅ Créé : admin_test (admin) - ID: 123e4567-e89b-12d3-a456-426614174000
✅ Créé : pharmacien_test (pharmacien) - ID: 223e4567-e89b-12d3-a456-426614174001
⚠️  medecin_test existe déjà (ID: 323e4567-e89b-12d3-a456-426614174002)
✅ Créé : patient_test (patient) - ID: 423e4567-e89b-12d3-a456-426614174003

============================================================
📊 RÉSUMÉ
============================================================
✅ Créés : 3
⚠️  Ignorés (déjà existants) : 1

👥 Utilisateurs créés :
   - admin_test (admin)
   - pharmacien_test (pharmacien)
   - patient_test (patient)

⚠️  Utilisateurs déjà existants :
   - medecin_test

============================================================
🔑 INFORMATIONS DE CONNEXION
============================================================

Vous pouvez maintenant vous connecter avec :

ADMIN:
  Username: admin_test
  Password: admin123456
  Email: admin@test.com

PHARMACIEN:
  Username: pharmacien_test
  Password: pharmacien123456
  Email: pharmacien@test.com

PATIENT:
  Username: patient_test
  Password: patient123456
  Email: patient@test.com

💡 Pour obtenir un token JWT, utilisez :
   curl -X POST 'http://localhost:8000/api/v1/auth/login' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'username=admin_test&password=admin123456'
```

---

## 🌐 Méthode Alternative : API Endpoint

Si vous préférez utiliser l'API, l'endpoint `/auth/create-test-users` est disponible mais **protégé** (admin uniquement).

### Prérequis

1. Vous devez avoir un compte admin
2. Vous devez obtenir un token JWT

### Étapes

**1. Se connecter en tant qu'admin** :
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin_test&password=admin123456"
```

**Réponse** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**2. Créer les utilisateurs tests** :
```bash
curl -X POST "http://localhost:8000/api/v1/auth/create-test-users" \
  -H "Authorization: Bearer <votre_token_admin>" \
  -H "Content-Type: application/json"
```

**Réponse** :
```json
{
  "message": "Created 4 test users",
  "users": [
    "admin_test",
    "pharmacien_test",
    "medecin_test",
    "patient_test"
  ]
}
```

---

## 🔐 Sécurité

### Pourquoi le script est recommandé ?

1. **Pas besoin d'authentification** : Le script accède directement à la base de données
2. **Plus simple** : Pas besoin de gérer les tokens JWT
3. **Sécurisé** : Ne peut être exécuté que localement sur votre machine
4. **Idéal pour le développement** : Création rapide d'utilisateurs de test

### Pourquoi l'endpoint API est protégé ?

L'endpoint `/auth/create-test-users` est protégé avec `require_admin` pour éviter :
- La création non autorisée d'utilisateurs en production
- Les abus de l'API publique
- Les problèmes de sécurité

---

## 🧪 Tester la connexion

Après avoir créé les utilisateurs, testez la connexion :

```bash
# Se connecter
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin_test&password=admin123456"

# Utiliser le token pour accéder à un endpoint protégé
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer <votre_token>"
```

---

## 📝 Notes

- Les utilisateurs créés sont **uniquement pour le développement**
- Ne pas utiliser ces mots de passe en production
- Les utilisateurs existants ne seront pas recréés (pas de doublons)
- Le script peut être exécuté plusieurs fois sans problème

---

## 🐛 Dépannage

### Erreur : "Module not found"
**Solution** : Assurez-vous d'être dans le répertoire `move4epilepsy-api` et que le venv est activé.

### Erreur : "Connection refused"
**Solution** : Vérifiez que PostgreSQL est démarré et que les variables d'environnement `.env` sont correctes.

### Erreur : "User already exists"
**Solution** : C'est normal, le script ignore les utilisateurs existants. Si vous voulez les recréer, supprimez-les d'abord de la base de données.
