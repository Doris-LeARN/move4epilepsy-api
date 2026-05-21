"""
Dépendances FastAPI pour l'authentification
Déplacé ici pour éviter les imports circulaires
"""
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.security import decode_access_token
from app.database.base import get_db
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# OAuth2 scheme pour l'authentification (keepalive pour docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Pour les endpoints qui acceptent les requêtes anonymes
optional_bearer = HTTPBearer(auto_error=False)


def get_token_from_cookie(access_token: Optional[str] = Cookie(None)) -> Optional[str]:
    """Extrait le token JWT depuis le cookie HttpOnly"""
    return access_token


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupère un utilisateur par son username"""
    from app.models.user import User
    return db.query(User).filter(User.username == username).first()


def get_current_user(
    token: Optional[str] = Depends(get_token_from_cookie),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur actuel depuis le cookie HttpOnly"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    
    # Charger le profil
    if not user.profile:
        db.refresh(user)
    
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_cookie),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Récupère l'utilisateur actuel depuis le cookie HttpOnly (optionnel pour endpoints anonymes)"""
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = get_user_by_username(db, username)
        if user:
            if not user.profile:
                db.refresh(user)
        return user
    except Exception as e:
        logger.warning("Token validation error: %s", type(e).__name__)
        return None


def get_current_user_required(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur actuel depuis le token JWT (requis)"""
    return get_current_user(token, db)
