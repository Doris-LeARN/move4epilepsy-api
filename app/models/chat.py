"""
Modèles Chat
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database.base import Base


class ChatChannel(Base):
    """Modèle canal de chat"""
    __tablename__ = "chat_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="", nullable=True)
    type = Column(String, nullable=False)  # 'general', 'support', 'medication', 'professional'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    messages = relationship("ChatMessage", back_populates="channel", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Modèle message de chat"""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)  # CHECK length > 0 AND length <= 2000
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_reported = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    channel = relationship("ChatChannel", back_populates="messages")
    user = relationship("User")


class MessageReport(Base):
    """Modèle signalement de message"""
    __tablename__ = "message_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False)  # 'pending', 'reviewed', 'resolved'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
