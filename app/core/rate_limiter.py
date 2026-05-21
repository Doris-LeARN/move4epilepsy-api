"""
Configuration centralisée du rate limiting (slowapi)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Créer une instance unique du limiter
limiter = Limiter(key_func=get_remote_address)
