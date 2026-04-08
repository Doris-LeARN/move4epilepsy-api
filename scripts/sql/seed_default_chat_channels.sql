-- Canaux de chat par défaut (PostgreSQL, idempotent par nom).
-- Exécuter avec : psql $DATABASE_URL -f scripts/sql/seed_default_chat_channels.sql

INSERT INTO chat_channels (id, name, description, type, is_active)
SELECT gen_random_uuid(), 'Général', 'Discussions ouvertes entre membres de la communauté.', 'general', true
WHERE NOT EXISTS (SELECT 1 FROM chat_channels WHERE name = 'Général');

INSERT INTO chat_channels (id, name, description, type, is_active)
SELECT gen_random_uuid(), 'Soutien', 'Entraide et accompagnement entre patients.', 'support', true
WHERE NOT EXISTS (SELECT 1 FROM chat_channels WHERE name = 'Soutien');

INSERT INTO chat_channels (id, name, description, type, is_active)
SELECT gen_random_uuid(), 'Traitements', 'Échanges sur les médicaments et le vécu du traitement (sans poser de diagnostic).', 'medication', true
WHERE NOT EXISTS (SELECT 1 FROM chat_channels WHERE name = 'Traitements');

INSERT INTO chat_channels (id, name, description, type, is_active)
SELECT gen_random_uuid(), 'Professionnels de santé', 'Espace dédié aux échanges avec ou entre professionnels.', 'professional', true
WHERE NOT EXISTS (SELECT 1 FROM chat_channels WHERE name = 'Professionnels de santé');
