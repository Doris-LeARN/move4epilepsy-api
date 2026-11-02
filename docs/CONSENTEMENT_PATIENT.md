# Parcours de consentement et gestion des déclarations patient

## Parcours d'une nouvelle déclaration

1. `POST /api/v1/patients/treatments/email-verification/request` avec `purpose: "registration"` envoie un code à six chiffres. La réponse ne révèle pas si l'adresse possède déjà des déclarations.
2. `POST /api/v1/patients/treatments/email-verification/confirm` vérifie le code et renvoie un `verification_token` temporaire.
3. Après la case de consentement, le frontend appelle `POST /api/v1/patients/treatments/consent` avec l'adresse, ce jeton, `consent_analysis`, `consent_alerts: true` et `consent_text_version`. L'API enregistre l'heure du consentement et renvoie un `consent_draft_token`.
4. La fenêtre de récapitulatif présente les informations de traitement et les finalités acceptées. Sa confirmation finale appelle `POST /api/v1/patients/treatments` avec les champs du traitement, les deux jetons et l'adresse. Cette requête crée la déclaration, enregistre l'heure de confirmation, consomme les jetons et fixe `email_verified: true`.

Le consentement aux alertes est obligatoire dans ce parcours et distinct du consentement facultatif à l'analyse. Une alerte est envoyée pour chaque transition déclarée d'un stock indisponible vers un stock disponible, si le médicament et la localisation correspondent à la déclaration. La création d'une ligne de stock déjà disponible n'est pas considérée comme un retour en stock. Le courriel reste générique et ne contient aucun détail de santé. Le texte de consentement fourni à l'écran doit être identifié par `PATIENT_CONSENT_TEXT_VERSION`; une version différente de celle configurée par l'API est rejetée. Il doit préciser les finalités, le caractère obligatoire des alertes, leur fréquence et la manière de retirer le consentement. La base légale, notamment pour les données de santé, doit être validée par les responsables compétents avant la mise en production.

## Récupération et gestion

1. `POST /api/v1/patients/treatments/email-verification/request` avec `purpose: "management"` envoie un code de connexion.
2. Le même endpoint `.../confirm` renvoie une `session_token` temporaire.
3. Le frontend transmet ce jeton dans `Authorization: Bearer <session_token>` :
   - `GET /api/v1/patients/treatments/mine` liste les déclarations rattachées à l'adresse vérifiée.
   - `PATCH /api/v1/patients/treatments/mine/{treatment_id}` modifie les champs de déclaration, mais pas l'adresse ni les preuves de consentement.
   - `DELETE /api/v1/patients/treatments/mine` supprime une ou plusieurs déclarations de manière atomique.
   - `POST /api/v1/patients/treatments/mine/consent/withdraw` requiert `confirm_withdrawal: true` et supprime les déclarations choisies, ce qui arrête leurs alertes.
   - `POST /api/v1/patients/treatments/mine/session/revoke` révoque la session.

Les codes expirent après 10 minutes, sont à usage unique et limités à cinq tentatives. Les demandes sont limitées à une par minute et cinq par heure pour une adresse. Le jeton de vérification peut servir à créer plusieurs déclarations pendant 20 minutes, avec un nouveau consentement et une confirmation distincts pour chaque déclaration. Les sessions expirent après 30 minutes. Seuls les condensats des codes et jetons sont persistés. Ils ne doivent pas être placés dans les URL ni ajoutés aux journaux.

Les traitements historiques sans adresse vérifiée ne sont pas récupérables par ce mécanisme. Les déclarations nouvellement créées restent anonymes vis-à-vis d'un compte utilisateur; l'adresse de contact est conservée uniquement pour les alertes et la gestion par e-mail vérifié.

## Exploitation et confidentialité

Configurer `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` et, le cas échéant, `SMTP_USE_STARTTLS` avant d'activer les parcours. L'API échoue explicitement si l'envoi du code n'est pas disponible et n'expose jamais le code dans sa réponse.

Les alertes en échec restent en attente et sont retentées lors d'une prochaine mise à jour du stock concerné ; l'exploitant doit surveiller les erreurs SMTP et définir un mécanisme opérationnel de reprise si nécessaire. Si l'API renvoie `503` pour une erreur de livraison, le stock et l'événement d'alerte sont déjà enregistrés ; répéter la mise à jour du stock permet de retenter l'envoi sans créer un second événement. Les délais d'effacement des sauvegardes doivent également être définis et communiqués par l'exploitant; la suppression effectuée par les routes ci-dessus concerne immédiatement la base applicative et ses statistiques, pas les sauvegardes hors ligne.

Exécuter `python -m scripts.migrate_patient_consent_workflow` avant le déploiement sur une base existante. Les anciens enregistrements restent marqués `email_verified: false` et ne sont pas visibles dans le nouvel espace personnel.
