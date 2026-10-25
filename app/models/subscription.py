"""
Modèles Abonnements
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class SubscriptionPlan(Base):
    """Modèle plan d'abonnement"""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    annual_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False)
    features = Column(JSON, default=list)
    max_stock_entries = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relations
    subscriptions = relationship("PharmacySubscription", back_populates="plan")


class CountryPricing(Base):
    """Modèle tarification par pays"""
    __tablename__ = "country_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    country = Column(String, unique=True, nullable=False)
    country_code = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    base_monthly_price = Column(Numeric(10, 2), nullable=False)
    purchasing_power_index = Column(Numeric(5, 2), default=50.0)
    preferred_payment_methods = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True, nullable=False)


class PharmacySubscription(Base):
    """Modèle abonnement pharmacie"""
    __tablename__ = "pharmacy_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)
    status = Column(String, default="trial", nullable=False)  # 'trial', 'active', 'expired', 'cancelled'
    start_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    auto_renew = Column(Boolean, default=True, nullable=False)
    billing_country = Column(String, nullable=True)
    billing_period = Column(String, default="monthly", nullable=False)
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    pharmacy = relationship("Pharmacy")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = relationship("SubscriptionPayment", back_populates="subscription")


class SubscriptionPayment(Base):
    """Modèle paiement d'abonnement"""
    __tablename__ = "subscription_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)  # 'mobile_money', 'card', 'bank_transfer', 'cash'
    payment_provider = Column(String, nullable=True)  # 'orange_money', 'mtn_momo', 'moov', 'stripe'
    transaction_id = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # 'pending', 'completed', 'failed', 'refunded'
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relations
    subscription = relationship("PharmacySubscription", back_populates="payments")
