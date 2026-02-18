#!/bin/bash
# Script pour lancer l'API avec le bon environnement

# Aller dans le dossier de l'API
cd "$(dirname "$0")"

# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier que SQLAlchemy est installé
python3 -c "import sqlalchemy" 2>/dev/null || {
    echo "❌ SQLAlchemy n'est pas installé. Installation..."
    pip install -r requirements.txt
}

# Lancer l'API
echo "🚀 Lancement de l'API..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
