"""
Modèles Pharmacy
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class Pharmacy(Base):
    """Modèle pharmacie"""
    __tablename__ = "pharmacies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pharmacy_id = Column(String, unique=True, nullable=False, index=True)  # ID PHARMACIE pour auth
    name = Column(String, nullable=False)
    license_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    postal_code = Column(String, nullable=True)
    country = Column(String, default="Bénin", nullable=False)
    department = Column(String, nullable=False)
    commune = Column(String, nullable=False)
    arrondissement = Column(String, nullable=True)
    quartier = Column(String, nullable=True)
    responsible_first_name = Column(String, nullable=False)
    responsible_last_name = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    user = relationship("User", back_populates="pharmacy")
    stocks = relationship("PharmacyStock", back_populates="pharmacy")


class PharmacyStock(Base):
    """Modèle stock pharmacie - Correspond exactement à Supabase"""
    __tablename__ = "pharmacy_stocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    is_rupture = Column(Boolean, default=False, nullable=False)
    last_update = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    declared_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Colonnes ajoutées dans market_failure_features
    medication_name = Column(String, nullable=True, index=True)  # Ajouté pour compatibilité
    price = Column(Numeric(10, 2), default=0, nullable=True)
    restock_delay = Column(String, nullable=True)
    min_order_quantity = Column(Integer, default=1, nullable=True)
    rupture_history = Column(JSONB, default=list, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relations
    pharmacy = relationship("Pharmacy", back_populates="stocks")
    medication = relationship("Medication", back_populates="stocks")
