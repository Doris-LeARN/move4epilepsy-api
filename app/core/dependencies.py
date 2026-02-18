"""
Dépendances FastAPI pour l'authentification
Déplacé ici pour éviter les imports circulaires
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.security import decode_access_token
from app.database.base import get_db
from app.models.user import User

# OAuth2 scheme pour l'authentification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Pour les endpoints qui acceptent les requêtes anonymes
optional_bearer = HTTPBearer(auto_error=False)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupère un utilisateur par son username"""
    from app.models.user import User
    return db.query(User).filter(User.username == username).first()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur actuel depuis le token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Récupère l'utilisateur actuel depuis le token JWT (optionnel pour endpoints anonymes)"""
    if credentials is None:
        return None
    
    try:
        payload = decode_access_token(credentials.credentials)
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
    except Exception:
        return None


def get_current_user_required(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur actuel depuis le token JWT (requis)"""
    return get_current_user(token, db)
