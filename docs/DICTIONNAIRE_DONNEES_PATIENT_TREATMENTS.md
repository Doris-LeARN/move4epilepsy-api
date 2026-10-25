# Dictionnaire de donnees - `patient_treatments`

Ce document decrit les champs presents dans `patient_treatments` et le parcours de gestion des declarations par e-mail verifie. Les champs ajoutes pour ce parcours sont inclus ci-dessous ; l'envoi des alertes de disponibilite et les exigences de conservation des sauvegardes restent a finaliser.

## Vue d'ensemble

- **Nom de la table**: `patient_treatments`
- **Modele SQLAlchemy**: `PatientTreatment`
- **Usage**: collecte de donnees de sante, d'acces au traitement, de cout et de retour d'experience. Ces donnees ne sont pas anonymes du seul fait qu'aucun nom ou compte patient n'est requis.
- **Implementation actuelle**: les nouvelles declarations conservent l'adresse e-mail verifiee et une preuve versionnee du consentement. Les declarants sans compte peuvent consulter, modifier et supprimer leurs declarations apres une verification e-mail.
- **Exigence cible**: adresse e-mail verifiee requise pour les alertes de disponibilite et la gestion des declarations ; consentement enregistre avec ses versions et horodatages ; consultation, modification, suppression individuelle ou groupee apres verification de cette adresse.

## Colonnes

| Colonne | Type (SQLAlchemy) | Nullable | Defaut | Description metier |
|---|---|---|---|---|
| `id` | `UUID` | Non | `uuid.uuid4` | Identifiant unique de l'enregistrement. |
| `name` | `String` | Oui | `""` | Nom ou pseudonyme libre facultatif. Peut contenir une information identifiante ; ne pas le presenter comme anonyme. |
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
| `wants_alert` | `Boolean` | Oui | `False` | Champ historique de souhait d'alerte. Le parcours produit cible rend l'adresse e-mail requise pour les alertes de disponibilite ; ce booléen seul ne prouve ni la verification de l'adresse ni le consentement. |
| `contact_email` | `String` | Oui | - | Adresse verifiee de gestion et d'alertes ; ne pas exposer dans les API publiques ou statistiques. Les anciennes declarations n'ont pas d'adresse associee. |
| `email_verified` | `Boolean` | Non | `False` | Indique qu'une verification de l'adresse a ete effectuee. |
| `email_verified_at` | `DateTime(timezone=True)` | Oui | - | Horodatage de la verification de l'adresse. |
| `consent_analysis` | `Boolean` | Oui | - | Consentement distinct a l'utilisation pour l'analyse. |
| `consent_alerts` | `Boolean` | Oui | - | Consentement aux alertes de disponibilite, requis dans le parcours actuel. |
| `consent_text_version` | `String` | Oui | - | Version du texte presente lors du consentement. |
| `consented_at` | `DateTime(timezone=True)` | Oui | - | Horodatage du choix initial de consentement. |
| `consent_confirmed_at` | `DateTime(timezone=True)` | Oui | - | Horodatage de la confirmation finale du recapitulatif. |
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
- Les champs medicaux, demographiques, geographiques et financiers peuvent permettre une identification indirecte et doivent etre proteges comme donnees personnelles de sante.

## Consentement, verification et gestion des acces

La migration `migrate_patient_consent_workflow.py` ajoute les champs et tables necessaires. Le contrat HTTP detaille est decrit dans `CONSENTEMENT_PATIENT.md`.

### Contact de gestion et d'alertes

Associer une adresse verifiee a la declaration (dans une table de contact dediee ou via une relation equivalentement protegee) :

| Donnee cible | Description et regle |
|---|---|
| `contact_email` | Adresse requise pour la gestion self-service et les alertes ; donnee personnelle associee a des donnees de sante. Ne jamais l'inclure dans les dashboards, exports analytiques ou API publiques. |
| `email_verified_at` | Horodatage confirmant la verification de la boite e-mail. Aucune gestion de declaration avant verification. |

Les alertes de disponibilite sont requises dans le parcours produit retenu. Ne pas reutiliser l'adresse pour du marketing ou une autre finalite non presentee et validee. Les courriels doivent contenir le minimum d'information necessaire et ne pas exposer les details cliniques.

### Preuve de consentement

La preuve est actuellement conservee avec la declaration dans `patient_treatments` :

| Donnee cible | Description et regle |
|---|---|
| `treatment_id` | Reference interne a la declaration ; jamais exposee comme facteur d'autorisation a elle seule. |
| `purpose` | Finalites distinguees par `consent_analysis` et `consent_alerts`. |
| `accepted` | Decision explicite stockee pour chacune des finalites. |
| `notice_version` | Version exacte de l'information/texte presente au moment du choix, stockee dans `consent_text_version`. |
| `consented_at` | Date/heure du consentement donne dans le formulaire. |
| `confirmed_at` | Date/heure de la confirmation finale, stockee dans `consent_confirmed_at`. |
| `withdrawn_at` | Non conserve separement : le retrait supprime les declarations selectionnees. La conservation d'une preuve de retrait doit etre validee selon la base legale et la politique de retention applicables. |

Le formulaire presente le choix initial ; le recapitulatif complet est confirme avant l'insertion definitive. Le backend doit recevoir et persister les choix et versions utiles ; un simple booléen d'interface n'est pas une preuve suffisante. Le responsable du traitement determine et documente les bases legales, les conditions applicables aux donnees de sante et la duree de conservation de la preuve. Les journaux d'audit ne doivent pas copier le contenu medical ni les codes de verification.

### Codes temporaires d'acces

Les codes de verification e-mail et sessions de gestion sont temporaires, limites en tentatives et stockes sous forme de condensats. Ils ne figurent ni dans les URL ni dans les journaux. Une session de gestion de 30 minutes ne donne acces qu'aux declarations associees a l'adresse verifiee.

### Suppression et analyses

- La personne peut modifier une declaration, ou selectionner une ou plusieurs declarations associees a son adresse verifiee pour suppression.
- Une suppression groupee est atomique. Le retrait du consentement arrete les alertes concernees et declenche la suppression des declarations concernees selon la regle produit validee.
- Les declarations supprimees sont exclues des vues, caches, taches d'alertes et calculs analytiques. Seuls des agregats irreversiblement anonymises peuvent etre conserves.
- Documenter les delais de purge des sauvegardes et toute exception legale. Ne pas affirmer une suppression immediata de copies non encore purgees.
