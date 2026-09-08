"""
Endpoints d'authentification
"""
from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, Union
from datetime import timedelta, datetime, timezone
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.permissions import require_admin
from app.core.dependencies import oauth2_scheme, optional_bearer, get_current_user, get_current_user_optional, get_current_user_required
from app.core.rate_limiter import limiter
from app.database.base import get_db
from app.models.user import User, UserProfile, PasswordResetToken
from app.models.patient import PatientTreatment
from app.models.opinion import UserOpinion
from app.schemas.user import UserCreate, UserResponse, UserProfileCreate, UserProfileResponse
from app.schemas.auth import Token
import secrets
import logging

logger = logging.getLogger(__name__)

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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime le compte et les données personnelles associées de l'utilisateur connecté."""
    db.query(PatientTreatment).filter(PatientTreatment.user_id == current_user.id).delete(synchronize_session=False)
    db.query(UserOpinion).filter(UserOpinion.user_id == current_user.id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == current_user.id).delete(synchronize_session=False)
    db.query(UserProfile).filter(UserProfile.user_id == current_user.id).delete(synchronize_session=False)
    db.delete(current_user)
    db.commit()
    return None


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


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    email: str,
    db: Session = Depends(get_db)
):
    """
    Envoie un email de réinitialisation de mot de passe
    
    NOTE: En développement, le token est retourné dans la réponse pour les tests.
    En production, il faudrait envoyer un email avec le lien de réinitialisation.
    """
    # Rechercher l'utilisateur par email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Pour éviter de révéler si un email existe, retourner un message générique
        logger.warning(f"Forgot password requested for non-existent email: {email}")
        return {
            "message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation"
        }
    
    # Générer un token de réinitialisation unique
    reset_token = secrets.token_urlsafe(32)
    
    # Définir l'expiration à 24h
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Nettoyer les anciens tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).delete()
    
    # Créer un nouveau token
    db_token = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    
    # TODO: Envoyer un email avec le lien: /reset-password?token={reset_token}
    # Pour les tests en développement, retourner le token
    if settings.DEBUG:
        return {
            "message": "Token de réinitialisation généré",
            "token": reset_token,  # À NE PAS RETOURNER EN PRODUCTION
        }
    
    return {
        "message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation"
    }


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Réinitialise le mot de passe avec un token valide
    """
    # Valider le token
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Vérifier l'expiration
    if datetime.now(timezone.utc) > db_token.expires_at:
        # Supprimer le token expiré
        db.delete(db_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Récupérer l'utilisateur
    user = db.query(User).filter(User.id == db_token.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Mettre à jour le mot de passe
    user.hashed_password = get_password_hash(new_password)
    
    # Supprimer tous les tokens de réinitialisation de cet utilisateur
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).delete()
    
    db.commit()
    
    logger.info(f"Password reset successful for user: {user.username}")
    
    return {
        "message": "Password reset successful. You can now login with your new password."
    }
