"""
Modèles Alertes
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class Alert(Base):
    """Modèle alerte bidirectionnelle"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type = Column(String, nullable=False)
    medication_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    recipient_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    recipient_type = Column(String, nullable=False)  # 'patient' or 'pharmacy'
    location = Column(String, nullable=True)
    metadata_json = Column("metadata", JSONB, default=dict)  # 'metadata' est réservé en SQLAlchemy, on utilise metadata_json comme attribut Python
    status = Column(String, default="pending", nullable=False, index=True)  # 'pending', 'sent', 'read'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)


class StockoutAlert(Base):
    """Modèle alerte de rupture de stock"""
    __tablename__ = "stockout_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medication_name = Column(String, nullable=False, index=True)
    patient_location = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)  # 'active', 'resolved'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
