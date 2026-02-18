"""
Test script pour vérifier que l'endpoint de routage fonctionne correctement
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import httpx

async def test_routing_endpoint():
    """Test l'endpoint de routage avec des coordonnées de test"""
    
    # Coordonnées de test : Cotonou (Bénin) -> Abomey-Calavi (Bénin)
    # Format: [lat, lng] pour le frontend, mais on envoie [lng, lat] à OpenRouteService
    start_lat, start_lng = 6.3654, 2.4184  # Cotonou
    end_lat, end_lng = 6.4489, 2.3553  # Abomey-Calavi
    
    # L'endpoint attend [lng, lat]
    start_param = f"{start_lng},{start_lat}"
    end_param = f"{end_lng},{end_lat}"
    
    url = f"http://localhost:8000/api/v1/routing/directions/driving-car"
    params = {
        "start": start_param,
        "end": end_param
    }
    
    print("🧪 Test de l'endpoint de routage")
    print(f"📍 Départ: Cotonou ({start_lat}, {start_lng})")
    print(f"📍 Arrivée: Abomey-Calavi ({end_lat}, {end_lng})")
    print(f"🔗 URL: {url}")
    print(f"📋 Paramètres: {params}\n")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("features") and len(data["features"]) > 0:
                    feature = data["features"][0]
                    geometry = feature["geometry"]["coordinates"]
                    distance_m = feature["properties"]["segments"][0]["distance"]
                    duration_s = feature["properties"]["segments"][0]["duration"]
                    
                    distance_km = distance_m / 1000
                    duration_min = duration_s / 60
                    
                    print("✅ Succès!")
                    print(f"   Distance: {distance_km:.2f} km")
                    print(f"   Durée: {duration_min:.1f} minutes")
                    print(f"   Points de géométrie: {len(geometry)}")
                    print(f"\n📐 Format de réponse:")
                    print(f"   - geometry.coordinates: [lng, lat] (comme OpenRouteService)")
                    print(f"   - Le frontend convertira en [lat, lng] pour Leaflet")
                    return True
                else:
                    print("❌ Erreur: Pas de features dans la réponse")
                    print(f"   Réponse: {data}")
                    return False
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                print(f"   Réponse: {response.text}")
                return False
                
    except httpx.ConnectError:
        print("❌ Erreur: Impossible de se connecter au serveur")
        print("   Assurez-vous que le serveur FastAPI est démarré sur http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_routing_endpoint())
    sys.exit(0 if success else 1)
