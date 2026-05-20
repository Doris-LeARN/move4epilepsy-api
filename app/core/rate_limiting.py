"""
Middleware pour le rate limiting et validation des inputs
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

# Initialiser le limiter global
limiter = Limiter(key_func=get_remote_address)

# Décorateurs de rate limiting pour différents types d'endpoints
def rate_limit_auth():
    """Rate limit pour endpoints d'authentification - Plus strict"""
    return limiter.limit("5/minute")  # 5 tentatives par minute

def rate_limit_api():
    """Rate limit pour endpoints API générales"""
    return limiter.limit("100/minute")  # 100 appels par minute

def rate_limit_public():
    """Rate limit pour endpoints publics"""
    return limiter.limit("200/minute")  # 200 appels par minute
