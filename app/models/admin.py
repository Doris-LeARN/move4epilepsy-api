"""
Modèles Administration
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class AdminActionLog(Base):
    """Modèle log des actions admin"""
    __tablename__ = "admin_actions_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(String, nullable=False, index=True)
    target_type = Column(String, nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relations
    admin = relationship("User", foreign_keys=[admin_id])


class UserSuspension(Base):
    """Modèle suspension d'utilisateur"""
    __tablename__ = "user_suspensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=False)
    suspended_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    suspended_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    lifted_at = Column(DateTime(timezone=True), nullable=True)
    lifted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relations
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])
    lifted_by_user = relationship("User", foreign_keys=[lifted_by])


class SystemSetting(Base):
    """Modèle paramètres système"""
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSONB, default=dict)
    description = Column(Text, default="", nullable=True)  # Valeur par défaut dans Supabase
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relations
    updater = relationship("User")
