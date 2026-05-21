"""
Endpoints d'authentification
"""
from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, Union
from datetime import timedelta
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.permissions import require_admin
from app.core.dependencies import oauth2_scheme, optional_bearer, get_current_user, get_current_user_optional, get_current_user_required
from app.core.rate_limiter import limiter
from app.database.base import get_db
from app.models.user import User, UserProfile
from app.schemas.user import UserCreate, UserResponse, UserProfileCreate, UserProfileResponse
from app.schemas.auth import Token

router = APIRouter()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupère un utilisateur par son username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Récupère un utilisateur par son email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Récupère un utilisateur par son ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Crée un nouvel utilisateur"""
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Les fonctions get_current_user, get_current_user_optional, get_current_user_required
# et oauth2_scheme sont maintenant dans app.core.dependencies pour éviter les imports circulaires


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # Rate limiting sur l'inscription
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Enregistre un nouvel utilisateur"""
    # Vérifier si l'utilisateur existe déjà
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Créer l'utilisateur
    user = create_user(db, user_data)
    
    # Créer le profil par défaut (patient)
    profile = UserProfile(
        user_id=user.id,
        username=user.username,
        role="patient",
    )
    db.add(profile)
    db.commit()
    
    return user


@router.post("/login", response_model=dict)
@limiter.limit("5/minute")  # Rate limiting sur le login
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = None,  # Pour set_cookie
    db: Session = Depends(get_db)
):
    """Connecte un utilisateur et retourne un HttpOnly cookie"""
    user = get_user_by_username(db, form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # ✅ HttpOnly Cookie (sécurisé contre XSS)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # ← JavaScript NE PEUT PAS accéder
        secure=settings.ENVIRONMENT == "production",  # HTTPS en prod
        samesite="strict",  # Protection CSRF
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Expiration
        path="/api",  # Limiter au chemin API
    )
    
    return {"message": "Login successful", "user_id": str(user.id)}


@router.post("/logout")
async def logout(response: Response):
    """Déconnecte l'utilisateur en supprimant le cookie HttpOnly"""
    response.delete_cookie(
        key="access_token",
        path="/api",
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
    )
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_required)):
    """Récupère les informations de l'utilisateur actuel"""
    return current_user


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère le profil de l'utilisateur actuel"""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.post("/create-test-users", status_code=status.HTTP_201_CREATED)
async def create_test_users(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),  # ✅ Sécurisé : Seuls les admins peuvent créer des utilisateurs tests
    db: Session = Depends(get_db)
):
    """
    Crée des utilisateurs de test pour le développement
    
    ⚠️ PROTÉGÉ : Seuls les administrateurs peuvent utiliser cet endpoint.
    Pour créer des utilisateurs tests sans être admin, utilisez le script :
    python scripts/create_test_users.py
    """
    test_users = [
        {
            "username": "admin_test",
            "email": "admin@test.com",
            "password": "admin123456",
            "role": "admin",
        },
        {
            "username": "pharmacien_test",
            "email": "pharmacien@test.com",
            "password": "pharmacien123456",
            "role": "pharmacien",
        },
        {
            "username": "medecin_test",
            "email": "medecin@test.com",
            "password": "medecin123456",
            "role": "medecin",
        },
        {
            "username": "patient_test",
            "email": "patient@test.com",
            "password": "patient123456",
            "role": "patient",
        },
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Vérifier si l'utilisateur existe déjà
        if get_user_by_username(db, user_data["username"]):
            continue
        
        user_create = UserCreate(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
        )
        user = create_user(db, user_create)
        
        # Créer le profil avec le rôle
        profile = UserProfile(
            user_id=user.id,
            username=user.username,
            role=user_data["role"],
        )
        db.add(profile)
        db.commit()
        
        created_users.append(user_data["username"])
    
    return {
        "message": f"Created {len(created_users)} test users",
        "users": created_users,
    }
