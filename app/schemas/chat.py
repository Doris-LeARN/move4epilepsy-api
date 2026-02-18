"""
Schémas Pydantic pour le chat
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class ChatChannelBase(BaseModel):
    """Schéma de base pour un canal"""
    name: str
    description: Optional[str] = None
    type: str  # 'general', 'support', 'medication', 'professional'
    is_active: bool = True


class ChatChannelCreate(ChatChannelBase):
    """Schéma pour la création d'un canal"""
    pass


class ChatChannelResponse(ChatChannelBase):
    """Schéma de réponse pour un canal"""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    """Schéma de base pour un message"""
    content: str


class ChatMessageCreate(ChatMessageBase):
    """Schéma pour la création d'un message"""
    channel_id: UUID


class ChatMessageResponse(BaseModel):
    """Schéma de réponse pour un message"""
    id: UUID
    channel_id: UUID
    user_id: Optional[UUID] = None
    content: str
    is_deleted: bool
    is_reported: bool
    created_at: datetime
    pseudonym: Optional[str] = None
    user_role: Optional[str] = None
    show_role: Optional[bool] = None

    class Config:
        from_attributes = True


class MessageReportCreate(BaseModel):
    """Schéma pour signaler un message"""
    message_id: UUID
    reason: str


class MessageReportResponse(BaseModel):
    """Schéma de réponse pour un signalement"""
    id: UUID
    message_id: UUID
    reported_by: Optional[UUID] = None
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
