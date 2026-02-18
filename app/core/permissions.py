"""
Gestion des permissions et rôles
"""
from fastapi import Depends, HTTPException, status
from typing import List
from app.core.dependencies import get_current_user
from app.models.user import User


def require_role(allowed_roles: List[str]):
    """
    Dépendance FastAPI pour vérifier le rôle de l'utilisateur
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.profile or current_user.profile.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return current_user
    
    return role_checker


def require_admin():
    """Dépendance pour vérifier que l'utilisateur est admin"""
    return require_role(["admin"])


def require_pharmacien():
    """Dépendance pour vérifier que l'utilisateur est pharmacien"""
    return require_role(["pharmacien", "admin"])


def require_medecin():
    """Dépendance pour vérifier que l'utilisateur est médecin"""
    return require_role(["medecin", "admin"])
