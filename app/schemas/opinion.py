"""
Schémas Pydantic pour les avis et perceptions
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class UserOpinionBase(BaseModel):
    """Schéma de base pour un avis"""
    author: str
    content: str
    rating: int  # 1-5
    category: Optional[str] = None


class UserOpinionCreate(UserOpinionBase):
    """Schéma pour la création d'un avis"""
    pass


class UserOpinionResponse(UserOpinionBase):
    """Schéma de réponse pour un avis"""
    id: UUID
    likes: int = 0
    dislikes: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PartnershipApplicationBase(BaseModel):
    """Schéma de base pour une candidature partenariat"""
    organization_type: str
    organization_name: str
    contact_person: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    address: str
    city: str
    postal_code: Optional[str] = None
    description: Optional[str] = None
    partnership_types: Optional[List[str]] = None
    resources: Optional[str] = None
    experience: Optional[str] = None
    motivation: Optional[str] = None


class PartnershipApplicationCreate(PartnershipApplicationBase):
    """Schéma pour la création d'une candidature"""
    pass


class PartnershipApplicationResponse(PartnershipApplicationBase):
    """Schéma de réponse pour une candidature"""
    id: UUID
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True


class MedicineReportBase(BaseModel):
    """Schéma de base pour un signalement médicament"""
    medicament: str
    pharmacy_name: str
    address: str
    city: str
    postal_code: Optional[str] = None
    price: Optional[Decimal] = None
    quantity_status: str
    reporter_name: str
    reporter_phone: str


class MedicineReportCreate(MedicineReportBase):
    """Schéma pour la création d'un signalement"""
    pass


class MedicineReportResponse(MedicineReportBase):
    """Schéma de réponse pour un signalement"""
    id: UUID
    verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class EpilepsyPerceptionBase(BaseModel):
    """Schéma de base pour une perception épilepsie"""
    age_range: str
    relationship_types: Optional[List[str]] = None
    danger_level: str
    normal_life: str
    contagious: str
    witness_experience: Optional[str] = None
    suggestions: Optional[str] = None


class EpilepsyPerceptionCreate(EpilepsyPerceptionBase):
    """Schéma pour la création d'une perception"""
    pass


class EpilepsyPerceptionResponse(EpilepsyPerceptionBase):
    """Schéma de réponse pour une perception"""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
