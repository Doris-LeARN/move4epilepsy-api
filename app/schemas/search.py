"""
Schémas Pydantic pour la recherche de médicaments
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class SearchParams(BaseModel):
    """Paramètres de recherche"""
    medication_id: UUID
    department: str
    commune: Optional[str] = None
    arrondissement: Optional[str] = None
    quartier: Optional[str] = None


class PharmacyInfo(BaseModel):
    """Informations d'une pharmacie"""
    id: UUID
    name: str
    address: str
    phone: Optional[str] = None
    department: str
    commune: str
    arrondissement: Optional[str] = None
    quartier: Optional[str] = None


class StockInfo(BaseModel):
    """Informations de stock"""
    quantity: int
    is_rupture: bool
    last_update: datetime


class SearchResult(BaseModel):
    """Résultat de recherche"""
    pharmacy: PharmacyInfo
    stock: StockInfo
    availability: str  # 'disponible' | 'indisponible' | 'non-confirme'


class AlertCreate(BaseModel):
    """Création d'une alerte"""
    medication_id: UUID
    department: str
    commune: Optional[str] = None
    arrondissement: Optional[str] = None
    quartier: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class AlertResponse(BaseModel):
    """Réponse pour une alerte"""
    id: UUID
    medication_id: UUID
    department: str
    commune: Optional[str] = None
    arrondissement: Optional[str] = None
    quartier: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    notified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
