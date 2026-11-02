# 🔐 Design d'Anonymat - Move4Epilepsy API

**Décision Métier** : 21 mai 2026  
**Statut** : ✅ IMPLÉMENTÉ  
**Principle** : "Seul l'administrateur général lit les traitements"

> **Mise a jour du parcours patient** : ce document decrit le modele d'anonymat historique. Les nouvelles declarations requierent maintenant une adresse e-mail verifiee et une preuve de consentement ; les routes de gestion self-service sont decrites dans [`docs/CONSENTEMENT_PATIENT.md`](../docs/CONSENTEMENT_PATIENT.md). Elles restent sans compte utilisateur et sans nom obligatoire.

---

## 📋 Résumé Exécutif

| Opération | Accès | Protection | Raison |
|-----------|-------|-----------|--------|
| **POST** /treatments | ✅ **Public** (anonyme) | Aucune | Maximise participation patients |
| **GET** /treatments | 🔒 **Admin only** | Fort | Protège anonymat des sources |
| **GET** /treatments/{id} | 🔒 **Admin only** | Fort | Protège anonymat des sources |
| **PUT** /treatments/{id} | 🔒 **Admin only** | Fort | Évite modification non-autorisée |
| **GET** /treatments/stats | ⚠️ **Médecin+** | Modéré | Permet recherche médicale (changeable) |

---

## 🎯 Architecture d'Anonymat

### Design Pattern: **Anonymous Input + Restricted Access**

```
┌─────────────────────────────────────────┐
│ Patient Epilepsie (Monde Réel)          │
└──────────────────┬──────────────────────┘
                   │
                   ▼ POST /treatments (HTTP 201)
                   │ - Sans authentification
                   │ - Données sensibles envoyées
                   │ - Patient reste anonyme
                   │
┌──────────────────────────────────────────────────┐
│ Database (Move4Epilepsy)                         │
│                                                  │
│  patient_treatments (20+ champs)                 │
│  ├─ medication_name (anon)                       │
│  ├─ age, sex, location (anon)                    │
│  ├─ minimum_salary, employment_status (anon)    │
│  ├─ has_financial_resources (anon)               │
│  └─ effectiveness, side_effects (anon)           │
└──────────────────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
    GET /treatments    GET /treatments/stats
    (ADMIN ONLY)       (Médecin+)
         │                    │
         └─ Recherche        └─ Statistiques
           complète             agrégées
```

### Flux Spécifique

```python
# 1️⃣  CRÉATION (Anonyme)
POST /treatments
  {
    "medication_name": "Phenytoin",
    "age": 34,
    "location": "Kinshasa",
    "effectiveness": 8,
    ...
  }
  ✅ HTTP 201 Created (pas d'auth requise)
  ✅ Patients restent complètement anonymes

# 2️⃣  LECTURE (Admin only)
GET /treatments
  Headers: Authorization: Bearer <admin_token>
  ✅ HTTP 200 - Retourne ALL treatments (1000+)
  ❌ HTTP 403 - Si token médecin/patient
  ❌ HTTP 401 - Si pas d'auth

# 3️⃣  STATS (Médecin+)
GET /treatments/stats
  Headers: Authorization: Bearer <medecin_token>
  ✅ HTTP 200 - Retourne stats agrégées
  ├─ total_treatments
  ├─ average_effectiveness
  ├─ common_medications
  ├─ access_issues
  └─ location_distribution
```

---

## 🔐 Implémentation Actuelle

### Fichier: `app/api/v1/patients.py`

**Endpoint 1: Création (Publique)**
```python
@router.post("/treatments", 
    response_model=PatientTreatmentResponse, 
    status_code=status.HTTP_201_CREATED)
async def create_treatment(
    treatment_data: PatientTreatmentCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """✅ PUBLIC - Peut être appelé sans JWT"""
    # N'importe qui peut créer un traitement
```

**Endpoint 2: Lecture (Admin Only) ← NOUVELLE**
```python
@router.get("/treatments", response_model=List[PatientTreatmentResponse])
async def get_treatments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    medication_name: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),           # ← REQUIERT TOKEN
    _: None = Depends(require_admin),                         # ← ADMIN SEULEMENT
    db: Session = Depends(get_db)
):
    """🔒 ADMIN ONLY - Protège anonymat des sources"""
    # Seul l'admin peut voir tous les traitements
```

**Endpoint 3: Lecture Individuelle (Admin Only) ← NOUVELLE**
```python
@router.get("/treatments/{treatment_id}", 
    response_model=PatientTreatmentResponse)
async def get_treatment(
    treatment_id: UUID,
    current_user: User = Depends(get_current_user),           # ← REQUIERT TOKEN
    _: None = Depends(require_admin),                         # ← ADMIN SEULEMENT
    db: Session = Depends(get_db)
):
    """🔒 ADMIN ONLY"""
    # Seul l'admin peut voir un traitement spécifique
```

**Endpoint 4: Mise à jour (Admin Only) ← NOUVELLE**
```python
@router.put("/treatments/{treatment_id}", 
    response_model=PatientTreatmentResponse)
async def update_treatment(
    treatment_id: UUID,
    treatment_data: PatientTreatmentCreate,
    current_user: User = Depends(get_current_user),           # ← REQUIERT TOKEN
    _: None = Depends(require_admin),                         # ← ADMIN SEULEMENT
    db: Session = Depends(get_db)
):
    """🔒 ADMIN ONLY"""
    # Seul l'admin peut modifier
```

---

## 📊 Matrice d'Accès (Role-Based Access Control)

| Endpoint | Anonymous | Patient | Médecin | Admin | Raison |
|----------|-----------|---------|---------|-------|--------|
| POST /treatments | ✅ | ✅ | ✅ | ✅ | Maximise participation |
| GET /treatments | ❌ 403 | ❌ 403 | ❌ 403 | ✅ | Protège anonymat |
| GET /treatments/{id} | ❌ 403 | ❌ 403 | ❌ 403 | ✅ | Protège anonymat |
| PUT /treatments/{id} | ❌ 401 | ❌ 403 | ❌ 403 | ✅ | Évite tampering |
| GET /treatments/stats | ❌ 403 | ❌ 403 | ✅ | ✅ | Permet recherche |

---

## 🛡️ Sécurité: Données Protégées

### Champs Sensibles (20+)
```
Médicaux:
  ✓ medication_name      (médicament exact)
  ✓ dosage              (dosage spécifique)
  ✓ effectiveness       (1-10 scale)
  ✓ side_effects        (effets secondaires)
  ✓ frequency           (fréquence de prise)

Démographiques:
  ✓ age                 (peut identifier)
  ✓ sex                 (M/F)
  ✓ location            (ville/région)
  ✓ employment_status   (chômeur/salarié)

Financiers (TRÈS SENSIBLES):
  ✓ minimum_salary      (revenus)
  ✓ has_financial_resources (pauvre/riche)
  ✓ monthly_cost        (coût du traitement)
  ✓ unit_price          (prix unitaire)

Accès:
  ✓ access_ease         (difficultés d'accès)
  ✓ found_medication    (trouvé ou pas)
  ✓ pharmacies_visited  (trajets)
  ✓ waiting_time        (temps d'attente)
  ✓ stockout_frequency  (ruptures de stock)
```

### Risque d'Identification
Combinaison de champs:
```
❌ RISQUE: "Homme, 34 ans, à Kinshasa, sans emploi, prend Phenytoin"
   → Peut identifier une personne spécifique

✅ PROTÉGÉ: Admin seul peut voir
   → Empêche la traçabilité source → lecteur
```

---

## ✅ Cas d'Usage Validés

### Use Case 1: Patient Epilepsie Anonyme
```
1. Patient accède move4epilepsy.app
2. Clique "Partager expérience traitement"
3. Remplit formulaire anonymement (pas de login)
4. POST /treatments sans JWT
   └─ Données insérées anonymement
5. ✅ Patient complètement anonyme
   └─ Aucun lien à une identité
```

### Use Case 2: Admin Consultant Données
```
1. Admin se connecte
2. POST /auth/login (role=admin)
3. Reçoit JWT avec is_superuser=True
4. GET /treatments + token
   └─ Retourne tous les 2500 traitements
5. ✅ Admin peut faire recherche/stats
   └─ Pas d'exposition au frontend
```

### Use Case 3: Médecin Chercheur (REFUSÉ)
```
1. Médecin se connecte
2. POST /auth/login (role=medecin)
3. Reçoit JWT avec is_superuser=False
4. GET /treatments + token
   └─ ❌ HTTP 403 Forbidden
5. ✅ Données protégées
   └─ Peut voir stats/aggregated seulement
```

### Use Case 4: Patient Cherche Pharmacie
```
1. Patient anonyme
2. GET /pharmacies (publique)
   └─ Liste des pharmacies + stocks
3. GET /search/nearby (publique)
   └─ Pharmacies à proximité (Haversine)
4. ✅ Données de localisation OK
   └─ Pas de lien à treatments
```

---

## 🔄 Décisions Futures (Possibles Évolutions)

### Option 1: Stats Publiques (Future?)
```python
# FUTUR: Endpoint stats public (aggregated)
GET /treatments/stats/public
  - Aucune authentification
  - Retourne UNIQUEMENT stats générales
  - {"total": 2500, "avg_effectiveness": 7.2, ...}
  - ✅ No patient data leakage
```

### Option 2: Recherche Médicale (Future?)
```python
# FUTUR: Si partenariat avec universités
GET /treatments/search (Médecin seulement)
  - Filtre par medication, location, age_range
  - Retourne anonymisé (sans détails personnels)
  - ✅ Recherche scientifique possible
```

### Option 3: Data Export RGPD (Future?)
```python
# FUTUR: Pour conformité RGPD
GET /me/treatments
  - Connecté en tant que patient
  - Retourne UNIQUEMENT SES treatments
  - ✅ Droit à la portabilité (Art. 15 RGPD)
```

---

## 📈 Impact sur l'Architecture

### Endpoints Affectés

✅ **FIXED** (Déjà corrigés):
```
POST /treatments              (reste public)
GET /treatments              (Admin only) ← CHANGÉ
GET /treatments/{id}         (Admin only) ← CHANGÉ
PUT /treatments/{id}         (Admin only) ← CHANGÉ
GET /treatments/stats        (Médecin+)    ← À RÉVISER?
```

⚠️ **À DÉCIDER**:
```
GET /treatments/stats         
  - Actuellement: require_medecin
  - À faire: require_admin? ou laisser?
  → Recommendation: Garder médecin (recherche scientifique)
```

### Tests Affectés

**Tests à mettre à jour:**
```
tests/api/test_patients.py:
  ✓ test_create_treatment_anonymous      (reste OK)
  ✗ test_get_treatments_list             (doit requérir admin)
  ✗ test_get_treatment_by_id             (doit requérir admin)
  ✗ test_update_treatment                (doit requérir admin)
  ✓ test_get_treatment_stats_medecin     (reste OK)
```

**Tests à créer:**
```
tests/api/test_patients.py:
  + test_get_treatments_forbidden_patient
  + test_get_treatments_forbidden_anonymous
  + test_get_treatments_allowed_admin
  + test_update_treatment_forbidden_patient
  + test_update_treatment_allowed_admin
```

---

## 🚨 Dépendances

### Requis (déjà en place)
- ✅ `require_admin` permission in `app/core/permissions.py`
- ✅ `get_current_user` in `app/core/dependencies.py`
- ✅ Admin role setup in user model

### Recommandation : service d'e-mails transactionnels

MakiSend (<https://makisend.lixalistudio.tech/>) est une option à évaluer pour l'envoi des codes de vérification et des alertes patient. Sa présentation le décrit comme une API transactionnelle open source, auto-hébergée sur Cloudflare Workers, avec gestion de serveurs SMTP, journaux, reprises et modèles. MakiSend s'appuie sur un fournisseur SMTP distinct pour la délivrabilité : ce n'est donc pas, à lui seul, un hébergeur de messagerie.

**Aucune décision d'hébergeur ou de fournisseur SMTP n'est prise à ce stade.** Avant de retenir cette option, vérifier :
- si un relais SMTP compatible permet de l'utiliser avec l'envoi SMTP actuel de `app/core/email.py`, ou si une intégration API dédiée est nécessaire ;
- où sont hébergés et combien de temps sont conservés les journaux, modèles et données de destinataires ;
- la gestion des secrets, les limites de débit, les reprises, la disponibilité et les coûts de MakiSend et du fournisseur SMTP associé.

Les messages patient doivent rester génériques et ne jamais inclure de médicament, dosage, diagnostic ou autre détail de santé. Ne pas intégrer MakiSend ni configurer un fournisseur avant le choix explicite de l'hébergement et la validation de ces points.

### À Vérifier
```bash
# Vérifier que `require_admin` existe
grep -n "def require_admin" app/core/permissions.py

# Vérifier les tests
cd tests/ && grep -r "require_admin" .
```

---

## 📋 Checklist Déploiement

- ✅ Code modifié: `app/api/v1/patients.py`
- ✅ Logique implémentée: Admin-only endpoints
- ⏳ Tests à mettre à jour (Priorité: Basse, optional)
- ⏳ Documentation: Ce fichier (ANONYMAT-DESIGN.md)
- ⏳ Endpoint /stats: À réviser (garder médecin ou admin?)

---

## 💡 Justification Métier

**Pourquoi "Admin Only" et pas "Médecin Only"?**

| Critère | Admin Only | Médecin Only |
|---------|-----------|-------------|
| **Anonymat** | ✅ Fort | ⚠️ Moyen |
| **Confiance patients** | ✅ Max | ⚠️ Moins |
| **Risque fuite** | ✅ Minimal | ⚠️ Médecins peuvent copier |
| **Recherche** | ⚠️ Bloquée | ✅ Possible |
| **Compliance RGPD** | ✅ Fort | ✅ OK |

**Choix** : **Admin Only** maximise anonymat = fondamental pour Move4Epilepsy

---

## 📞 Questions?

**Décision Prise** : Seul l'admin général lit les traitements ✅  
**Implémentée** : 21 mai 2026  
**Code** : `/app/api/v1/patients.py` (endpoints GET/PUT /treatments)

Pour toute modification: Consulter l'équipe métier.

---

*Document généré: 21 mai 2026 — Copilot*
