"""
Schémas Pydantic pour les médicaments
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class MedicationBase(BaseModel):
    """Schéma de base pour un médicament"""
    name: str
    dosage: str
    form: str = "Comprimé"
    active: bool = True


class MedicationCreate(MedicationBase):
    """Schéma pour la création d'un médicament"""
    pass


class MedicationUpdate(BaseModel):
    """Schéma pour la mise à jour d'un médicament"""
    name: Optional[str] = None
    dosage: Optional[str] = None
    form: Optional[str] = None
    active: Optional[bool] = None


class MedicationResponse(MedicationBase):
    """Schéma de réponse pour un médicament"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
