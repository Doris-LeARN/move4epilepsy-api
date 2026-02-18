"""
Schémas Pydantic pour les utilisateurs
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Schéma de base pour un utilisateur"""
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur"""
    password: str


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schéma de réponse pour un utilisateur"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schéma pour un utilisateur en base de données (inclut le hash du mot de passe)"""
    hashed_password: str


class UserProfileBase(BaseModel):
    """Schéma de base pour un profil utilisateur"""
    username: str
    role: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    phone: Optional[str] = ""


class UserProfileCreate(UserProfileBase):
    """Schéma pour la création d'un profil"""
    user_id: UUID


class UserProfileResponse(UserProfileBase):
    """Schéma de réponse pour un profil"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
