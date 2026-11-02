# Workflow – Scripts API Move4Epilepsy

Un seul fichier pour tous les usages. Prérequis : `cd move4epilepsy-api` puis `source venv/bin/activate`.  
`.env` doit contenir : `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (clé service_role, pas anon).

---

## 1. Première mise en place (base vide)

1. Créer la base PostgreSQL `move4epilepsy`.
2. Créer les tables et appliquer les colonnes du workflow patient :
   `python -m scripts.migrate_patient_consent_workflow`
3. Créer le référentiel de domaines et catégories médicaments :
   `python -m scripts.migrate_medication_categories`
4. Démarrer l’API.
5. Vérifier/corriger le schéma :
   `python scripts/verify_and_fix_schema.py`
6. Migrer les données depuis Supabase :
   `python scripts/migrate_from_supabase.py`
7. Si la table `medications` est vide :
   `python scripts/init_data.py`

---

## 2. Colonnes pgAdmin ≠ Swagger (schéma à jour)

- Lancer :  
  `python scripts/verify_and_fix_schema.py`  
- Le script compare les 26 tables aux modèles SQLAlchemy, propose les ALTER TABLE, demande confirmation puis les applique. Il indique aussi si des lignes `patient_treatments` manquent (Supabase vs PostgreSQL).

---

## 3. Migration complète Supabase → PostgreSQL

- Lancer :  
  `python scripts/migrate_from_supabase.py`  
- Vide les tables (avec confirmation), migre `auth.users` et les 26 tables, encodage UTF-8.  
- Si des enregistrements manquent (ex. `patient_treatments`) : revérifier `SUPABASE_SERVICE_ROLE_KEY` et relancer ce script.

---

## 4. Problème d’encodage (caractères mal affichés)

- D’abord : `python scripts/verify_and_fix_schema.py`  
- Si le problème reste :  
  `python scripts/migrate_force_utf8.py`

---

## 5. Après modification des modèles SQLAlchemy

1. Modifier les modèles dans `app/models/`.
2. Lancer :  
   `python scripts/verify_and_fix_schema.py`  
3. Tester l’API.

---

## Scripts (résumé)

| Script | Rôle |
|--------|------|
| `migrate_from_supabase.py` | Migration complète Supabase → PostgreSQL |
| `migrate_subscription_checkout_fields.py` | Ajouter le pays, la périodicité et le snapshot de prix aux souscriptions |
| `migrate_patient_consent_workflow.py` | Ajouter les champs de consentement et les tables OTP/session des déclarations patient |
| `migrate_medication_categories.py` | Ajouter les domaines et catégories thérapeutiques au référentiel médicaments |
| `verify_and_fix_schema.py` | Aligner les tables PostgreSQL sur les modèles (colonnes, types, NULL) + diagnostic `patient_treatments` |
| `migrate_force_utf8.py` | Correction UTF-8 (uniquement si besoin après migration) |
| `init_data.py` | Insérer les médicaments de base dans `medications` |

---

## Vérifications rapides (optionnel)

```bash
# Colonnes de souscription nécessaires au checkout
python scripts/migrate_subscription_checkout_fields.py

# Consentement et gestion vérifiée des déclarations patient
python -m scripts.migrate_patient_consent_workflow

# Domaines et catégories du référentiel médicaments
python -m scripts.migrate_medication_categories

# Connexion PostgreSQL
psql -U postgres -d move4epilepsy -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM patient_treatments;"
```

Les scripts demandent confirmation avant de modifier les données et ne suppriment pas de colonnes.
