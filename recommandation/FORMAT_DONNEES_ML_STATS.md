# Format de Données Optimisé pour Statistiques et Machine Learning

## 🎯 Objectif

Ce document décrit le format de données choisi pour faciliter les analyses statistiques et l'élaboration de modèles de machine learning précis et complets.

## 📊 Format Choisi : Dates ISO + Métriques Numériques

### Pourquoi ce format ?

1. **Dates ISO (YYYY-MM-DD)** : Format standardisé internationalement reconnu
   - Facile à parser dans tous les langages (Python, SQL, JavaScript)
   - Permet des calculs de durée précis
   - Compatible avec les fonctions SQL de date
   - Facilite les agrégations temporelles (par mois, année, etc.)

2. **Timestamps Unix (millisecondes)** : Pour calculs rapides
   - Comparaisons de dates ultra-rapides
   - Calculs de durée en une simple soustraction
   - Indexation efficace en base de données

3. **Métriques numériques pré-calculées** : Durée en jours, mois, années
   - Évite les calculs répétés lors des analyses
   - Facilite les agrégations statistiques
   - Prêt pour l'entraînement de modèles ML

## 📋 Structure des Données

### Format de `treatment_periods` (JSONB)

```json
{
  "periods": [
    {
      // Données originales
      "medicationName": "Depakine 300 mg",
      "dosage": "300 mg",
      "frequency": "2 fois par jour",
      "reasonForChange": "Effets secondaires",
      
      // Dates ISO normalisées (format optimal pour ML/Stats)
      "startDateISO": "2020-01-01",        // Format: YYYY-MM-DD
      "endDateISO": "2023-12-31",          // Format: YYYY-MM-DD ou null si en cours
      "startTimestamp": 1577836800000,      // Timestamp Unix (ms)
      "endTimestamp": 1704067199000,        // Timestamp Unix (ms) ou Date.now() si en cours
      "isOngoing": false,                   // Boolean pour identifier les traitements en cours
      
      // Métriques numériques calculées (pour ML/Stats)
      "durationDays": 1460,                 // Durée en jours (entier)
      "durationMonths": 48,                 // Durée en mois (arrondi)
      "durationYears": 4,                  // Durée en années (arrondi)
      
      // Champs de référence (pour compatibilité et affichage)
      "startMonth": "1",
      "startYear": "2020",
      "endMonth": "12",
      "endYear": "2023",
      
      // Index de période (pour ordre)
      "periodIndex": 0
    }
  ],
  "metadata": {
    // Métriques globales pour ML/Stats
    "totalDurationDays": 1460,
    "totalDurationMonths": 48,
    "totalDurationYears": 4,
    "totalPeriods": 1,
    "ongoingPeriods": 0,
    "completedPeriods": 1
  }
}
```

### Format de `treatment_duration` (String)

Chaîne lisible pour affichage sur le site :
- **Période unique avec dates** : `"Janvier 2020 - Décembre 2023"`
- **Période unique année seulement** : `"2020 - 2023"`
- **Traitement en cours** : `"Depuis Janvier 2020"`
- **Plusieurs périodes** : `"2020 - 2023 (3 périodes)"`

## 🔍 Avantages pour les Statistiques

### 1. Agrégations Temporelles Faciles

```sql
-- Compter les traitements par année
SELECT 
  EXTRACT(YEAR FROM (treatment_periods->'periods'->0->>'startDateISO')::date) as year,
  COUNT(*) as count
FROM patient_treatments
GROUP BY year;

-- Durée moyenne des traitements
SELECT 
  AVG((treatment_periods->'metadata'->>'totalDurationDays')::integer) as avg_duration_days
FROM patient_treatments;
```

### 2. Analyses de Durée

```python
# Python - Calculer la durée moyenne
import json
from statistics import mean

treatments = db.query(PatientTreatment).all()
durations = []
for t in treatments:
    if t.treatment_periods and 'metadata' in t.treatment_periods:
        durations.append(t.treatment_periods['metadata']['totalDurationDays'])

avg_duration = mean(durations)
```

### 3. Identification des Traitements en Cours

```sql
-- Trouver tous les traitements en cours
SELECT *
FROM patient_treatments
WHERE treatment_periods->'periods' @> '[{"isOngoing": true}]';
```

## 🤖 Avantages pour le Machine Learning

### 1. Features Prêtes à l'Emploi

Les métriques pré-calculées peuvent être directement utilisées comme features :

```python
# Features pour modèle ML
features = {
    'duration_days': period['durationDays'],
    'duration_months': period['durationMonths'],
    'duration_years': period['durationYears'],
    'is_ongoing': period['isOngoing'],
    'total_periods': metadata['totalPeriods'],
    'ongoing_periods': metadata['ongoingPeriods'],
}
```

### 2. Normalisation Temporelle

Les timestamps permettent des calculs précis :
- Gaps entre périodes de traitement
- Durée depuis le début du traitement
- Prédiction de fin de traitement

### 3. Agrégations Multi-Niveaux

```python
# Exemple : Prédire l'efficacité basée sur la durée
X = [
    treatment.treatment_periods['metadata']['totalDurationDays'],
    treatment.effectiveness,
    treatment.age
]
```

## 📈 Exemples d'Utilisation

### Statistiques Temporelles

```python
# Durée moyenne par médicament
SELECT 
  medication_name,
  AVG((treatment_periods->'metadata'->>'totalDurationDays')::integer) as avg_days,
  AVG((treatment_periods->'metadata'->>'totalDurationMonths')::integer) as avg_months
FROM patient_treatments
GROUP BY medication_name;
```

### Modèles de Prédiction

```python
# Features pour prédire l'efficacité
features = {
    'treatment_duration_days': metadata['totalDurationDays'],
    'number_of_periods': metadata['totalPeriods'],
    'has_ongoing_treatment': metadata['ongoingPeriods'] > 0,
    'age': treatment.age,
    'medication': treatment.medication_name,
}
```

### Analyses de Tendances

```python
# Évolution des durées de traitement par année
SELECT 
  EXTRACT(YEAR FROM created_at) as year,
  AVG((treatment_periods->'metadata'->>'totalDurationDays')::integer) as avg_duration
FROM patient_treatments
GROUP BY year
ORDER BY year;
```

## ✅ Résumé des Avantages

1. **Précision** : Dates ISO avec granularité jour
2. **Performance** : Métriques pré-calculées évitent les calculs répétés
3. **Flexibilité** : Format JSONB permet des requêtes complexes
4. **Compatibilité** : Standard ISO reconnu internationalement
5. **Lisibilité** : Chaîne lisible pour affichage utilisateur
6. **ML-Ready** : Features numériques directement exploitables

## 🔧 Migration

Le format est automatiquement calculé lors de l'enregistrement d'un traitement. Aucune migration nécessaire pour les nouvelles données.

Pour les données existantes, un script de migration peut être créé pour convertir les anciens formats vers ce nouveau format optimisé.
