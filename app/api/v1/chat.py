"""
Endpoints pour le chat communautaire
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.chat import ChatChannel, ChatMessage, MessageReport
from app.models.user import User, UserProfile
from app.schemas.chat import (
    ChatChannelResponse, ChatChannelCreate,
    ChatMessageResponse, ChatMessageCreate,
    MessageReportCreate, MessageReportResponse
)
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.permissions import require_admin

router = APIRouter()


@router.get("/channels", response_model=List[ChatChannelResponse])
async def get_channels(
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Récupère tous les canaux de chat (public)"""
    query = db.query(ChatChannel)
    
    if active_only:
        query = query.filter(ChatChannel.is_active == True)
    
    channels = query.order_by(ChatChannel.created_at).all()
    return channels


@router.get("/channels/{channel_id}", response_model=ChatChannelResponse)
async def get_channel(
    channel_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupère un canal par son ID"""
    channel = db.query(ChatChannel).filter(ChatChannel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    return channel


@router.get("/channels/{channel_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    channel_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Récupère les messages d'un canal"""
    # Vérifier que le canal existe
    channel = db.query(ChatChannel).filter(ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Récupérer les messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.channel_id == channel_id,
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrichir avec les pseudonymes
    result = []
    for msg in messages:
        pseudonym = None
        user_role = None
        
        if msg.user_id:
            profile = db.query(UserProfile).filter(UserProfile.user_id == msg.user_id).first()
            if profile:
                pseudonym = profile.username
                user_role = profile.role
        
        result.append(ChatMessageResponse(
            id=msg.id,
            channel_id=msg.channel_id,
            user_id=msg.user_id,
            content=msg.content,
            is_deleted=msg.is_deleted,
            is_reported=msg.is_reported,
            created_at=msg.created_at,
            pseudonym=pseudonym or "Anonyme",
            user_role=user_role,
            show_role=True,
        ))
    
    # Inverser pour avoir les plus anciens en premier
    return list(reversed(result))


@router.post("/channels/{channel_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    channel_id: UUID,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envoie un message dans un canal (authentifié)"""
    # Vérifier que le canal existe et est actif
    channel = db.query(ChatChannel).filter(
        ChatChannel.id == channel_id,
        ChatChannel.is_active == True
    ).first()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found or inactive"
        )
    
    # Créer le message
    message = ChatMessage(
        channel_id=channel_id,
        user_id=current_user.id,
        content=message_data.content.strip(),
        is_deleted=False,
        is_reported=False,
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Récupérer le pseudonyme
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    pseudonym = profile.username if profile else "Anonyme"
    user_role = profile.role if profile else None
    
    return ChatMessageResponse(
        id=message.id,
        channel_id=message.channel_id,
        user_id=message.user_id,
        content=message.content,
        is_deleted=message.is_deleted,
        is_reported=message.is_reported,
        created_at=message.created_at,
        pseudonym=pseudonym,
        user_role=user_role,
        show_role=True,
    )


@router.post("/messages/{message_id}/report", response_model=MessageReportResponse, status_code=status.HTTP_201_CREATED)
async def report_message(
    message_id: UUID,
    report_data: MessageReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Signale un message"""
    # Vérifier que le message existe
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Créer le signalement
    report = MessageReport(
        message_id=message_id,
        reported_by=current_user.id,
        reason=report_data.reason,
        status="pending",
    )
    
    # Marquer le message comme signalé
    message.is_reported = True
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un message (soft delete)"""
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Vérifier les permissions : utilisateur peut supprimer ses propres messages
    user_role = current_user.profile.role if current_user.profile else None
    
    if user_role not in ["admin"]:
        if message.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages"
            )
    
    message.is_deleted = True
    db.commit()
    
    return None


@router.post("/channels", response_model=ChatChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChatChannelCreate,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crée un nouveau canal (admin uniquement)"""
    channel = ChatChannel(**channel_data.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    return channel
