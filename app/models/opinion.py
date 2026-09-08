"""
Modèles Opinion et Partenariats
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Numeric, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class UserOpinion(Base):
    """Modèle avis utilisateur"""
    __tablename__ = "user_opinions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    author = Column(String, default="", nullable=False)  # Valeur par défaut dans Supabase
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # CHECK >= 1 AND <= 5
    category = Column(String, default="Général", nullable=False)  # NOT NULL avec défaut dans Supabase
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PartnershipApplication(Base):
    """Modèle candidature partenariat"""
    __tablename__ = "partnership_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_type = Column(String, nullable=False)
    organization_name = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    postal_code = Column(String, nullable=True)
    description = Column(Text, nullable=False)  # NOT NULL dans Supabase
    partnership_types = Column(ARRAY(String), default=list, nullable=False)  # NOT NULL avec défaut dans Supabase
    resources = Column(Text, nullable=False)  # NOT NULL dans Supabase
    experience = Column(Text, nullable=True)
    motivation = Column(Text, nullable=False)  # NOT NULL dans Supabase
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MedicineReport(Base):
    """Modèle signalement médicament"""
    __tablename__ = "medicine_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medicament = Column(String, nullable=False)
    pharmacy_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    postal_code = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # NOT NULL dans Supabase
    quantity_status = Column(String, nullable=False)  # CHECK IN ('disponible', 'stock-limite', 'derniere-boite', 'sur-commande')
    reporter_name = Column(String, nullable=True)  # Nullable dans Supabase
    reporter_phone = Column(String, nullable=True)  # Nullable dans Supabase
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EpilepsyPerception(Base):
    """Modèle perception épilepsie"""
    __tablename__ = "epilepsy_perceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    age_range = Column(String, nullable=False)
    relationship_types = Column(ARRAY(String), nullable=True)
    danger_level = Column(String, nullable=False)
    normal_life = Column(String, nullable=False)
    contagious = Column(String, nullable=False)
    witness_experience = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
