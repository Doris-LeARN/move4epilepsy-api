"""
Endpoints pour le routage et les directions (proxy OpenRouteService)
Avec fallback sur calcul Haversine si l'API échoue
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import os
import traceback
from app.core.config import settings
from app.core.geoutils import haversine_distance, estimate_driving_time

# Import httpx avec gestion d'erreur
try:
    import httpx
except ImportError:
    httpx = None
    print("⚠️ WARNING: httpx n'est pas installé. Installez-le avec: pip install httpx")

router = APIRouter()

# Clé API OpenRouteService depuis les variables d'environnement
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY", "5b3ce3597851110001cf6248e8c8e8c8b8c8e8c8b8c8e8c8b8c8e8c8b")


@router.get("/directions/driving-car")
async def get_directions(
    start: str = Query(..., description="Coordonnées de départ au format 'lng,lat'"),
    end: str = Query(..., description="Coordonnées d'arrivée au format 'lng,lat'"),
):
    """
    Proxy pour l'API OpenRouteService - Calcul de directions en voiture
    Résout les problèmes CORS en faisant la requête depuis le backend
    En cas d'échec de l'API, utilise un calcul de distance approximatif (Haversine)
    """
    # Parser les coordonnées
    try:
        start_parts = start.split(',')
        end_parts = end.split(',')
        
        if len(start_parts) != 2 or len(end_parts) != 2:
            raise ValueError("Format de coordonnées invalide")
        
        start_lng, start_lat = float(start_parts[0]), float(start_parts[1])
        end_lng, end_lat = float(end_parts[0]), float(end_parts[1])
        
        # Coordonnées au format (lat, lng) pour Haversine
        start_coord = (start_lat, start_lng)
        end_coord = (end_lat, end_lng)
        
    except (ValueError, IndexError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Format de coordonnées invalide. Attendu: 'lng,lat'. Erreur: {str(e)}"
        )
    
    # Essayer d'abord avec OpenRouteService si httpx est disponible
    if httpx is not None:
        try:
            # Construire l'URL de l'API OpenRouteService
            url = f"https://api.openrouteservice.org/v2/directions/driving-car"
            
            params = {
                "api_key": OPENROUTESERVICE_API_KEY,
                "start": start,
                "end": end
            }
            
            # Faire la requête avec httpx (asynchrone)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Si erreur 403 ou autre, utiliser le fallback
                    error_detail = response.text[:200] if response.text else "Unknown error"
                    print(f"⚠️ OpenRouteService API error (status {response.status_code}): {error_detail}")
                    print("🔄 Utilisation du calcul de distance approximatif (Haversine)")
                    
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"⚠️ Erreur de connexion à OpenRouteService: {str(e)}")
            print("🔄 Utilisation du calcul de distance approximatif (Haversine)")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'appel à OpenRouteService: {str(e)}")
            print("🔄 Utilisation du calcul de distance approximatif (Haversine)")
    
    # Fallback: Calcul de distance approximatif avec Haversine
    try:
        distance_km = haversine_distance(start_coord, end_coord)
        duration_minutes = estimate_driving_time(distance_km)
        
        # Créer une réponse au format OpenRouteService pour compatibilité
        # Générer quelques points intermédiaires pour le polyline (approximation)
        num_points = max(10, int(distance_km * 2))  # Plus de points pour les longues distances
        polyline = []
        
        for i in range(num_points + 1):
            ratio = i / num_points
            lat = start_coord[0] + (end_coord[0] - start_coord[0]) * ratio
            lng = start_coord[1] + (end_coord[1] - start_coord[1]) * ratio
            polyline.append([lng, lat])  # Format [lng, lat] comme OpenRouteService
        
        fallback_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": polyline
                    },
                    "properties": {
                        "segments": [
                            {
                                "distance": distance_km * 1000,  # En mètres
                                "duration": duration_minutes * 60  # En secondes
                            }
                        ],
                        "summary": {
                            "distance": distance_km * 1000,
                            "duration": duration_minutes * 60
                        }
                    }
                }
            ],
            "metadata": {
                "note": "Distance calculée avec formule Haversine (approximation en ligne droite)"
            }
        }
        
        print(f"✅ Distance calculée (Haversine): {distance_km:.2f} km, durée estimée: {duration_minutes:.1f} min")
        return fallback_response
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        error_msg = f"Erreur lors du calcul de distance: {str(e)}"
        print(f"❌ Erreur lors du calcul de distance: {error_msg}")
        print(f"📋 Traceback complet:\n{error_traceback}")
        raise HTTPException(
            status_code=500,
            detail=f"{error_msg}. Type: {type(e).__name__}"
        )
