"""
Modèle Medication
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class Medication(Base):
    """Modèle médicament"""
    __tablename__ = "medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    form = Column(String, default="Comprimé", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    stocks = relationship("PharmacyStock", back_populates="medication", cascade="all, delete-orphan")
    searches = relationship("PatientSearch", back_populates="medication", cascade="all, delete-orphan")
    alerts = relationship("SearchAlert", back_populates="medication", cascade="all, delete-orphan")
