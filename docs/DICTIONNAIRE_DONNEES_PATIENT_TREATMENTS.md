# Dictionnaire de donnees - `patient_treatments`

Ce document decrit les champs de la table `patient_treatments` utilises pour enregistrer les traitements des patients.

## Vue d'ensemble

- **Nom de la table**: `patient_treatments`
- **Modele SQLAlchemy**: `PatientTreatment`
- **Usage**: collecte de donnees cliniques, d'acces au traitement, de cout et de retour d'experience patient.

## Colonnes

| Colonne | Type (SQLAlchemy) | Nullable | Defaut | Description metier |
|---|---|---|---|---|
| `id` | `UUID` | Non | `uuid.uuid4` | Identifiant unique de l'enregistrement. |
| `name` | `String` | Oui | `""` | Nom ou pseudonyme du patient (anonymisable). |
| `age` | `Integer` | Non | - | Age du patient. |
| `sex` | `String` | Non | - | Sexe du patient (`homme`, `femme`, `autre`, `non-specifie`). |
| `location` | `String` | Non | - | Localisation geographique declaree par le patient. |
| `medication_name` | `String` | Non | - | Nom du medicament pris (champ texte, indexe). |
| `dosage` | `String` | Non | - | Dosage du traitement. |
| `frequency` | `String` | Non | - | Frequence de prise (ex: nombre de prises par jour). |
| `treatment_duration` | `Integer` | Oui | - | Duree du traitement en mois. |
| `treatment_start_date` | `DateTime(timezone=True)` | Oui | - | Date de debut du traitement. |
| `treatment_end_date` | `DateTime(timezone=True)` | Oui | - | Date de fin du traitement. |
| `treatment_is_ongoing` | `Boolean` | Oui | `False` | Indique si le traitement est encore en cours. |
| `monthly_cost` | `String` | Oui | - | Cout mensuel estime du traitement. |
| `unit_price` | `String` | Oui | - | Prix unitaire du medicament. |
| `access_ease` | `String` | Non | - | Niveau de facilite d'acces au traitement. |
| `effectiveness` | `Integer` | Non | - | Note d'efficacite du traitement (1 a 10). |
| `side_effects` | `Text` | Oui | `""` | Effets secondaires rapportes. |
| `difficulties` | `Text` | Oui | `""` | Difficultes rencontrees pendant le traitement. |
| `additional_comments` | `Text` | Oui | `""` | Commentaires libres complementaires. |
| `found_medication` | `String` | Oui | - | Information sur la disponibilite du medicament (trouve ou non). |
| `pharmacies_visited` | `String` | Oui | - | Nombre ou liste de pharmacies visitees. |
| `waiting_time` | `String` | Oui | - | Temps d'attente pour obtenir le medicament. |
| `stockout_frequency` | `String` | Oui | - | Frequence percue des ruptures de stock. |
| `wants_alert` | `Boolean` | Oui | `False` | Souhait de recevoir une alerte de disponibilite/reassort. |
| `morning_pills` | `String` | Oui | - | Prise/comprime(s) du matin. |
| `noon_pills` | `String` | Oui | - | Prise/comprime(s) du midi. |
| `evening_pills` | `String` | Oui | - | Prise/comprime(s) du soir. |
| `education_level` | `String` | Oui | - | Niveau d'education du patient. |
| `minimum_salary` | `String` | Oui | - | Information de revenu/salaire minimum declaree. |
| `employment_status` | `String` | Oui | - | Situation professionnelle du patient. |
| `has_financial_resources` | `String` | Oui | - | Capacite financiere percue pour assumer le traitement. |
| `has_alternative_medication` | `Boolean` | Oui | - | Presence d'une alternative therapeutique connue/utilisee. |
| `alternative_medication_name` | `String` | Oui | - | Nom de l'alternative therapeutique, si applicable. |
| `knows_restock_delay` | `Boolean` | Oui | - | La pharmacie a-t-elle communique un delai de reassort. |
| `is_restock_delay_precise` | `Boolean` | Oui | - | Le delai de reassort annonce est-il juge precis. |
| `restock_delay_precise` | `String` | Oui | - | Delai precis annonce (ex: `2-3 jours`). |
| `action_when_delay_unknown` | `String` | Oui | - | Action entreprise par le patient si le delai n'est pas connu/precis. |
| `created_at` | `DateTime(timezone=True)` | Non | `now()` | Date de creation de l'enregistrement. |

## Notes

- Ce dictionnaire est derive du modele `PatientTreatment` dans `app/models/patient.py`.
- Certaines regles de validation (ex: bornes, enum logique) peuvent aussi etre appliquees cote API/schema, en plus de la base.
