#!/bin/bash
# 🚀 Quick Start Script - Move4Epilepsy API
# Lance l'API rapidement en développement local avec Docker

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🚀 Move4Epilepsy API - Quick Start"
echo "=================================="
echo ""

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Installe Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose v2 n'est pas installé."
    exit 1
fi

echo "✅ Docker trouvé: $(docker --version)"
echo "✅ Docker Compose trouvé: $(docker compose version --short)"
echo ""

# Vérifier .env
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Édite .env et définis une SECRET_KEY!"
    echo "   Génère une clé forte:"
    echo "   python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo ""
fi

# Demander si on lance Docker
read -p "Démarrer les containers Docker ? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🐳 Lancement des containers..."
    docker compose up -d
    
    # Attendre que l'API soit prête
    echo ""
    echo "⏳ Attente du démarrage de l'API..."
    sleep 5
    
    # Vérifier la santé
    API_READY=0
    for i in {1..30}; do
        if curl -s http://localhost:3003/health > /dev/null 2>&1; then
            API_READY=1
            echo "✅ API prête!"
            break
        fi
        echo "  Tentative $i/30..."
        sleep 2
    done

    if [ "$API_READY" -ne 1 ]; then
        echo "❌ L'API n'a pas démarré. Derniers logs :"
        docker compose logs --tail=100 api
        exit 1
    fi
    
    echo ""
    echo "🎉 Succès! Ouvre les URLs:"
    echo "   📍 API:       http://localhost:3003"
    echo "   📖 Docs:      http://localhost:3003/docs"
    echo "   🗄️  Database:  postgresql://postgres:postgres@localhost:5432/move4epilepsy"
    echo ""
    echo "📝 Logs:"
    echo "   docker compose logs -f api      # Logs API"
    echo ""
    echo "⛔ Arrêter:"
    echo "   docker compose down"
    echo ""
else
    echo "ℹ️  Pour démarrer manuellement:"
    echo "   docker compose up -d api"
    exit 0
fi
