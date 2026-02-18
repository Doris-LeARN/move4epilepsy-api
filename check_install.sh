#!/bin/bash
# Script pour vérifier l'installation

cd "$(dirname "$0")"

echo "🔍 Vérification de l'installation..."

# Vérifier si venv existe
if [ ! -d "venv" ]; then
    echo "❌ Le dossier 'venv' n'existe pas. Création..."
    python3 -m venv venv
fi

# Activer venv
source venv/bin/activate

echo "📦 Vérification des modules..."

# Vérifier chaque module
modules=("fastapi" "sqlalchemy" "psycopg2" "jose" "passlib" "pydantic")

for module in "${modules[@]}"; do
    python3 -c "import $module" 2>/dev/null && echo "✅ $module installé" || echo "❌ $module MANQUANT"
done

echo ""
echo "📋 Si des modules manquent, exécute :"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
