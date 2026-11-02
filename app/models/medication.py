"""
Modèle Medication
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class MedicationDomain(Base):
    """Top-level medical domain for medication reference categories."""
    __tablename__ = "medication_domains"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    categories = relationship("MedicationCategory", back_populates="domain")


class MedicationCategory(Base):
    """Validated therapeutic category within a medication domain."""
    __tablename__ = "medication_categories"

    id = Column(String, primary_key=True)
    domain_id = Column(
        String,
        ForeignKey("medication_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    domain = relationship("MedicationDomain", back_populates="categories")
    medications = relationship("Medication", back_populates="category")


class Medication(Base):
    """Modèle médicament"""
    __tablename__ = "medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    form = Column(String, default="Comprimé", nullable=False)
    category_id = Column(
        String,
        ForeignKey("medication_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    category = relationship("MedicationCategory", back_populates="medications")
    stocks = relationship("PharmacyStock", back_populates="medication", cascade="all, delete-orphan")
    searches = relationship("PatientSearch", back_populates="medication", cascade="all, delete-orphan")
    alerts = relationship("SearchAlert", back_populates="medication", cascade="all, delete-orphan")
