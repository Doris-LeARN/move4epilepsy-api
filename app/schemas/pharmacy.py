"""
Schémas Pydantic pour les pharmacies
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PharmacyBase(BaseModel):
    """Schéma de base pour une pharmacie"""
    name: str
    license_number: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: str
    city: str
    postal_code: Optional[str] = None
    country: str = "Bénin"
    department: str
    commune: str
    arrondissement: Optional[str] = None
    quartier: Optional[str] = None
    responsible_first_name: str
    responsible_last_name: str


class PharmacyCreate(PharmacyBase):
    """Schéma pour la création d'une pharmacie"""
    pharmacy_id: str  # ID PHARMACIE pour auth


class PharmacyUpdate(BaseModel):
    """Schéma pour la mise à jour d'une pharmacie"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    active: Optional[bool] = None


class PharmacyResponse(PharmacyBase):
    """Schéma de réponse pour une pharmacie"""
    id: UUID
    pharmacy_id: str
    user_id: Optional[UUID] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockBase(BaseModel):
    """Schéma de base pour un stock"""
    medication_id: UUID
    quantity: int
    is_rupture: bool = False


class StockCreate(StockBase):
    """Schéma pour la création d'un stock"""
    pass


class StockResponse(StockBase):
    """Schéma de réponse pour un stock"""
    id: UUID
    pharmacy_id: UUID
    last_update: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PharmacyWithStocks(PharmacyResponse):
    """Pharmacie avec ses stocks"""
    stocks: List[StockResponse] = []
