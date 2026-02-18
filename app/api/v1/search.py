"""
Endpoints pour la recherche de médicaments et alertes
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.database.base import get_db
from app.models.medication import Medication
from app.models.patient import SearchAlert
from app.schemas.search import SearchParams, SearchResult, AlertCreate, AlertResponse
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_search_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db)
):
    """Crée une alerte de recherche"""
    # Vérifier que le médicament existe
    medication = db.query(Medication).filter(Medication.id == alert_data.medication_id).first()
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    # Créer l'alerte
    alert = SearchAlert(
        medication_id=alert_data.medication_id,
        department=alert_data.department,
        commune=alert_data.commune,
        arrondissement=alert_data.arrondissement,
        quartier=alert_data.quartier,
        contact_email=alert_data.contact_email,
        contact_phone=alert_data.contact_phone,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert


@router.get("/alerts", response_model=List[AlertResponse])
async def get_search_alerts(
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupère les alertes de recherche"""
    query = db.query(SearchAlert).filter(SearchAlert.is_active == True)
    
    if email:
        query = query.filter(SearchAlert.contact_email == email)
    if phone:
        query = query.filter(SearchAlert.contact_phone == phone)
    
    alerts = query.order_by(SearchAlert.created_at.desc()).all()
    return alerts


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_search_alert(
    alert_id: UUID,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Met à jour une alerte (pour la désactiver)"""
    alert = db.query(SearchAlert).filter(SearchAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    if is_active is not None:
        alert.is_active = is_active
    
    db.commit()
    db.refresh(alert)
    
    return alert


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_alert(
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """Supprime une alerte"""
    alert = db.query(SearchAlert).filter(SearchAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    db.delete(alert)
    db.commit()
    
    return None
