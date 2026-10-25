"""
Schémas Pydantic pour les abonnements
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class SubscriptionPlanBase(BaseModel):
    """Schéma de base pour un plan"""
    name: str
    country: str
    monthly_price: Decimal = Field(gt=0)
    annual_price: Decimal = Field(gt=0)
    currency: str
    features: List[Any] = Field(default_factory=list)
    max_stock_entries: int = 100
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schéma pour la création d'un plan"""
    pass


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """Schéma de réponse pour un plan"""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PharmacySubscriptionBase(BaseModel):
    """Schéma de base pour un abonnement"""
    pharmacy_id: UUID
    plan_id: UUID
    status: str
    start_date: datetime
    end_date: datetime
    auto_renew: bool = True
    billing_country: Optional[str] = None
    billing_period: Literal["monthly", "annual"] = "monthly"
    amount: Optional[Decimal] = None
    currency: Optional[str] = None


class PharmacySubscriptionCreate(BaseModel):
    """Schéma pour la création d'un abonnement"""
    plan_id: UUID
    billing_country: str = Field(min_length=2, max_length=100)
    billing_period: Literal["monthly", "annual"] = "monthly"
    auto_renew: bool = True


class PharmacySubscriptionResponse(PharmacySubscriptionBase):
    """Schéma de réponse pour un abonnement"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    plan: Optional[SubscriptionPlanResponse] = None

    class Config:
        from_attributes = True


class SubscriptionPaymentCreate(BaseModel):
    """Schéma pour la création d'un paiement"""
    subscription_id: UUID
    payment_method: str
    payment_provider: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None


class SubscriptionPaymentResponse(BaseModel):
    """Schéma de réponse pour un paiement"""
    id: UUID
    subscription_id: Optional[UUID] = None
    pharmacy_id: Optional[UUID] = None
    amount: Decimal
    currency: str
    payment_method: str
    payment_provider: Optional[str] = None
    transaction_id: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
