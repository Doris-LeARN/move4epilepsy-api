#!/bin/bash
set -e

cd "$(dirname "$0")"

VENV_DIR="${VENV_DIR:-.venv}"
if [ ! -x "$VENV_DIR/bin/uvicorn" ]; then
    VENV_DIR="venv"
fi

if [ ! -x "$VENV_DIR/bin/uvicorn" ]; then
    echo "❌ Environnement Python introuvable. Créez-le puis installez les dépendances :"
    echo "   python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Lancement de l'API..."
exec "$VENV_DIR/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port "${PORT:-8002}"
