"""
Endpoints pour les avis, perceptions et partenariats
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.opinion import (
    UserOpinion, PartnershipApplication,
    MedicineReport, EpilepsyPerception
)
from app.schemas.opinion import (
    UserOpinionResponse, UserOpinionCreate,
    PartnershipApplicationResponse, PartnershipApplicationCreate,
    MedicineReportResponse, MedicineReportCreate,
    EpilepsyPerceptionResponse, EpilepsyPerceptionCreate
)
from app.core.permissions import require_admin
from app.core.dependencies import get_current_user, get_current_user_optional
from app.models.user import User

router = APIRouter()


# ========== AVIS UTILISATEURS ==========

@router.get("/opinions", response_model=List[UserOpinionResponse])
async def get_opinions(
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Récupère les avis utilisateurs (public)"""
    query = db.query(UserOpinion)
    
    if category:
        query = query.filter(UserOpinion.category == category)
    
    opinions = query.order_by(UserOpinion.created_at.desc()).offset(skip).limit(limit).all()
    return opinions


@router.post("/opinions", response_model=UserOpinionResponse, status_code=status.HTTP_201_CREATED)
async def create_opinion(
    opinion_data: UserOpinionCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Crée un avis (public, anonyme autorisé)"""
    # Valider le rating
    if opinion_data.rating < 1 or opinion_data.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    opinion = UserOpinion(
        **opinion_data.model_dump(),
        user_id=current_user.id if current_user else None,
    )
    db.add(opinion)
    db.commit()
    db.refresh(opinion)
    
    return opinion


@router.delete("/opinions/{opinion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opinion(
    opinion_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime un avis appartenant à l'utilisateur connecté ou à un administrateur."""
    opinion = db.query(UserOpinion).filter(UserOpinion.id == opinion_id).first()
    if not opinion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opinion not found")

    is_admin = current_user.profile is not None and current_user.profile.role == "admin"
    if not is_admin and opinion.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own opinions")

    db.delete(opinion)
    db.commit()
    return None


# ========== PARTENARIATS ==========

@router.get("/partnerships", response_model=List[PartnershipApplicationResponse])
async def get_partnership_applications(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Récupère les candidatures partenariats (admin uniquement)"""
    query = db.query(PartnershipApplication)
    
    if status:
        query = query.filter(PartnershipApplication.status == status)
    
    applications = query.order_by(PartnershipApplication.created_at.desc()).offset(skip).limit(limit).all()
    return applications


@router.post("/partnerships", response_model=PartnershipApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_partnership_application(
    application_data: PartnershipApplicationCreate,
    db: Session = Depends(get_db)
):
    """Crée une candidature partenariat (public)"""
    application = PartnershipApplication(**application_data.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application


@router.put("/partnerships/{application_id}", response_model=PartnershipApplicationResponse)
async def update_partnership_application(
    application_id: UUID,
    status: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Met à jour le statut d'une candidature (admin uniquement)"""
    application = db.query(PartnershipApplication).filter(
        PartnershipApplication.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partnership application not found"
        )
    
    application.status = status
    db.commit()
    db.refresh(application)
    
    return application


# ========== SIGNALEMENTS MÉDICAMENTS ==========

@router.get("/medicine-reports", response_model=List[MedicineReportResponse])
async def get_medicine_reports(
    verified: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Récupère les signalements médicaments (admin uniquement)"""
    query = db.query(MedicineReport)
    
    if verified is not None:
        query = query.filter(MedicineReport.verified == verified)
    
    reports = query.order_by(MedicineReport.created_at.desc()).offset(skip).limit(limit).all()
    return reports


@router.post("/medicine-reports", response_model=MedicineReportResponse, status_code=status.HTTP_201_CREATED)
async def create_medicine_report(
    report_data: MedicineReportCreate,
    db: Session = Depends(get_db)
):
    """Crée un signalement médicament (public)"""
    report = MedicineReport(**report_data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report


@router.put("/medicine-reports/{report_id}/verify", response_model=MedicineReportResponse)
async def verify_medicine_report(
    report_id: UUID,
    verified: bool = True,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Marque un signalement comme vérifié (admin uniquement)"""
    report = db.query(MedicineReport).filter(MedicineReport.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine report not found"
        )
    
    report.verified = verified
    db.commit()
    db.refresh(report)
    
    return report


# ========== PERCEPTIONS ÉPILEPSIE ==========

@router.get("/epilepsy-perceptions", response_model=List[EpilepsyPerceptionResponse])
async def get_epilepsy_perceptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Récupère les perceptions épilepsie (public)"""
    perceptions = db.query(EpilepsyPerception).order_by(
        EpilepsyPerception.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return perceptions


@router.post("/epilepsy-perceptions", response_model=EpilepsyPerceptionResponse, status_code=status.HTTP_201_CREATED)
async def create_epilepsy_perception(
    perception_data: EpilepsyPerceptionCreate,
    db: Session = Depends(get_db)
):
    """Crée une perception épilepsie (public, anonyme autorisé)"""
    perception = EpilepsyPerception(**perception_data.model_dump())
    db.add(perception)
    db.commit()
    db.refresh(perception)
    
    return perception
