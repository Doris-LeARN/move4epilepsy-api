"""
Schémas Pydantic pour l'authentification
"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Modèle de réponse pour un token"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Données du token"""
    username: Optional[str] = None
