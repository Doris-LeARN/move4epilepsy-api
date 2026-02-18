"""
Endpoints pour l'administration
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.user import User, UserProfile
from app.models.medication import Medication
from app.models.pharmacy import Pharmacy, PharmacyStock
from app.models.patient import PatientTreatment
from app.models.chat import ChatMessage, MessageReport
from app.models.subscription import PharmacySubscription
from app.models.opinion import PartnershipApplication, MedicineReport
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_admin
from pydantic import BaseModel

router = APIRouter()


class DashboardStats(BaseModel):
    """Statistiques du tableau de bord admin"""
    total_users: int
    total_pharmacies: int
    total_medications: int
    total_treatments: int
    active_subscriptions: int
    pending_partnerships: int
    pending_reports: int
    recent_messages: int


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques du tableau de bord admin"""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_pharmacies = db.query(func.count(Pharmacy.id)).scalar() or 0
    total_medications = db.query(func.count(Medication.id)).scalar() or 0
    total_treatments = db.query(func.count(PatientTreatment.id)).scalar() or 0
    
    active_subscriptions = db.query(func.count(PharmacySubscription.id)).filter(
        PharmacySubscription.status.in_(["active", "trial"])
    ).scalar() or 0
    
    pending_partnerships = db.query(func.count(PartnershipApplication.id)).filter(
        PartnershipApplication.status == "pending"
    ).scalar() or 0
    
    pending_reports = db.query(func.count(MessageReport.id)).filter(
        MessageReport.status == "pending"
    ).scalar() or 0
    
    # Messages des dernières 24h
    from datetime import datetime, timedelta
    recent_messages = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.created_at >= datetime.utcnow() - timedelta(days=1)
    ).scalar() or 0
    
    return DashboardStats(
        total_users=total_users,
        total_pharmacies=total_pharmacies,
        total_medications=total_medications,
        total_treatments=total_treatments,
        active_subscriptions=active_subscriptions,
        pending_partnerships=pending_partnerships,
        pending_reports=pending_reports,
        recent_messages=recent_messages,
    )


@router.get("/users", response_model=List[dict])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Récupère la liste des utilisateurs (admin uniquement)"""
    query = db.query(User).join(UserProfile)
    
    if role:
        query = query.filter(UserProfile.role == role)
    
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        profile = user.profile
        result.append({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": profile.role if profile else None,
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    
    return result


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Met à jour le rôle d'un utilisateur (admin uniquement)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.profile:
        # Créer un profil si inexistant
        profile = UserProfile(user_id=user.id, role=role)
        db.add(profile)
    else:
        user.profile.role = role
    
    db.commit()
    
    return {"message": "User role updated successfully"}


@router.put("/users/{user_id}/activate")
async def toggle_user_activation(
    user_id: UUID,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Active ou désactive un utilisateur (admin uniquement)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}


@router.get("/reports/messages", response_model=List[dict])
async def get_message_reports(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Récupère les signalements de messages (admin uniquement)"""
    query = db.query(MessageReport).join(ChatMessage)
    
    if status:
        query = query.filter(MessageReport.status == status)
    
    reports = query.order_by(desc(MessageReport.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for report in reports:
        message = db.query(ChatMessage).filter(ChatMessage.id == report.message_id).first()
        result.append({
            "id": str(report.id),
            "message_id": str(report.message_id),
            "message_content": message.content if message else None,
            "reported_by": str(report.reported_by) if report.reported_by else None,
            "reason": report.reason,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })
    
    return result


@router.put("/reports/messages/{report_id}")
async def update_message_report(
    report_id: UUID,
    status: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Met à jour le statut d'un signalement (admin uniquement)"""
    report = db.query(MessageReport).filter(MessageReport.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    report.status = status
    db.commit()
    
    return {"message": "Report status updated successfully"}


@router.get("/reports/medicines", response_model=List[dict])
async def get_medicine_reports(
    verified: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Récupère les signalements médicaments (admin uniquement)"""
    query = db.query(MedicineReport)
    
    if verified is not None:
        query = query.filter(MedicineReport.verified == verified)
    
    reports = query.order_by(desc(MedicineReport.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for report in reports:
        result.append({
            "id": str(report.id),
            "medicament": report.medicament,
            "pharmacy_name": report.pharmacy_name,
            "address": report.address,
            "city": report.city,
            "price": str(report.price) if report.price else None,
            "quantity_status": report.quantity_status,
            "reporter_name": report.reporter_name,
            "reporter_phone": report.reporter_phone,
            "verified": report.verified,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })
    
    return result
