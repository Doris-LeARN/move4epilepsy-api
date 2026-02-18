"""
Modèles Analytics
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class DemandAnalytics(Base):
    """Modèle analytics de demande"""
    __tablename__ = "demand_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    department = Column(String, nullable=False)
    commune = Column(String, nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    search_count = Column(Integer, default=0, nullable=False)
    alert_count = Column(Integer, default=0, nullable=False)
    availability_rate = Column(Numeric(5, 2), default=0, nullable=False)
    avg_price = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StockoutPrediction(Base):
    """Modèle prédiction de rupture"""
    __tablename__ = "stockout_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    pharmacy_id = Column(UUID(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_stockout_date = Column(DateTime(timezone=True), nullable=False)
    probability = Column(Numeric(5, 2), nullable=False)
    current_stock = Column(Integer, nullable=False)
    predicted_demand = Column(Integer, nullable=False)
    confidence_level = Column(Numeric(5, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
