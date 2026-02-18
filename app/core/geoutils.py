"""
Utilitaires de géolocalisation et calcul de distances
"""
import math
from typing import Tuple


def haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calcule la distance entre deux points géographiques en utilisant la formule Haversine
    Retourne la distance en kilomètres
    
    Args:
        coord1: Tuple (latitude, longitude) du premier point
        coord2: Tuple (latitude, longitude) du deuxième point
    
    Returns:
        Distance en kilomètres
    """
    # Rayon de la Terre en kilomètres
    R = 6371.0
    
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def estimate_driving_time(distance_km: float) -> float:
    """
    Estime le temps de trajet en voiture en minutes
    Basé sur une vitesse moyenne de 50 km/h en zone urbaine
    
    Args:
        distance_km: Distance en kilomètres
    
    Returns:
        Temps estimé en minutes
    """
    # Vitesse moyenne en km/h (50 km/h pour zone urbaine)
    average_speed_kmh = 50.0
    
    # Temps en heures, puis conversion en minutes
    time_hours = distance_km / average_speed_kmh
    time_minutes = time_hours * 60
    
    return time_minutes
