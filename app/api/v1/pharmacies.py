"""
Endpoints pour les pharmacies
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.pharmacy import Pharmacy, PharmacyStock
from app.models.medication import Medication
from app.schemas.pharmacy import (
    PharmacyResponse, PharmacyCreate, PharmacyUpdate,
    StockResponse, StockCreate, PharmacyWithStocks
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_pharmacien, require_admin

router = APIRouter()


@router.get("", response_model=List[PharmacyResponse])
async def get_pharmacies(
    active_only: bool = Query(True, description="Retourner uniquement les pharmacies actives"),
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    department: Optional[str] = Query(None, description="Filtrer par département"),
    db: Session = Depends(get_db)
):
    """Récupère toutes les pharmacies (publique)"""
    query = db.query(Pharmacy)
    
    if active_only:
        query = query.filter(Pharmacy.active == True)
    
    if city:
        query = query.filter(Pharmacy.city == city)
    
    if department:
        query = query.filter(Pharmacy.department == department)
    
    pharmacies = query.order_by(Pharmacy.name).all()
    return pharmacies


@router.get("/public/pharmacies-with-stocks", response_model=List[PharmacyWithStocks])
async def get_public_pharmacies_with_stocks(
    cities: Optional[str] = Query(None, description="Villes séparées par des virgules"),
    db: Session = Depends(get_db)
):
    """
    Récupère les pharmacies publiques avec leurs stocks.
    Déclaré avant /{pharmacy_id} pour que la route soit bien prise en compte.
    """
    query = db.query(Pharmacy).filter(Pharmacy.active == True)

    if cities:
        city_list = [c.strip() for c in cities.split(",")]
        query = query.filter(Pharmacy.city.in_(city_list))

    pharmacies = query.options(joinedload(Pharmacy.stocks)).all()

    result = []
    for pharmacy in pharmacies:
        stocks_data = [
            StockResponse(
                id=stock.id,
                pharmacy_id=stock.pharmacy_id,
                medication_id=stock.medication_id,
                quantity=stock.quantity,
                is_rupture=stock.is_rupture,
                last_update=stock.last_update,
                created_at=stock.created_at,
            )
            for stock in pharmacy.stocks
        ]
        pharmacy_data = PharmacyResponse(
            id=pharmacy.id,
            pharmacy_id=pharmacy.pharmacy_id,
            name=pharmacy.name,
            license_number=pharmacy.license_number,
            email=pharmacy.email,
            phone=pharmacy.phone,
            address=pharmacy.address,
            city=pharmacy.city,
            postal_code=pharmacy.postal_code,
            country=pharmacy.country,
            department=pharmacy.department,
            commune=pharmacy.commune,
            arrondissement=pharmacy.arrondissement,
            quartier=pharmacy.quartier,
            responsible_first_name=pharmacy.responsible_first_name,
            responsible_last_name=pharmacy.responsible_last_name,
            user_id=pharmacy.user_id,
            active=pharmacy.active,
            created_at=pharmacy.created_at,
            updated_at=pharmacy.updated_at,
        )
        result.append(PharmacyWithStocks(**pharmacy_data.model_dump(), stocks=stocks_data))

    return result


@router.get("/{pharmacy_id}", response_model=PharmacyResponse)
async def get_pharmacy(
    pharmacy_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupère une pharmacie par son ID"""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found"
        )
    
    return pharmacy


@router.get("/{pharmacy_id}/stocks", response_model=List[StockResponse])
async def get_pharmacy_stocks(
    pharmacy_id: UUID,
    medication_id: Optional[UUID] = Query(None, description="Filtrer par médicament"),
    db: Session = Depends(get_db)
):
    """Récupère les stocks d'une pharmacie"""
    # Vérifier que la pharmacie existe
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found"
        )
    
    query = db.query(PharmacyStock).filter(PharmacyStock.pharmacy_id == pharmacy_id)
    
    if medication_id:
        query = query.filter(PharmacyStock.medication_id == medication_id)
    
    stocks = query.order_by(PharmacyStock.last_update.desc()).all()
    return stocks


@router.post("/{pharmacy_id}/stocks", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_stock(
    pharmacy_id: UUID,
    stock_data: StockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée ou met à jour un stock (pharmacien uniquement)"""
    # Vérifier que la pharmacie existe
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found"
        )
    
    # Vérifier les permissions : pharmacien peut seulement modifier ses propres stocks
    if current_user.profile and current_user.profile.role == "pharmacien":
        if pharmacy.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage stocks for your own pharmacy"
            )
    
    # Vérifier que le médicament existe
    medication = db.query(Medication).filter(Medication.id == stock_data.medication_id).first()
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    # Chercher un stock existant
    existing_stock = db.query(PharmacyStock).filter(
        PharmacyStock.pharmacy_id == pharmacy_id,
        PharmacyStock.medication_id == stock_data.medication_id
    ).first()
    
    if existing_stock:
        # Mettre à jour
        existing_stock.quantity = stock_data.quantity
        existing_stock.is_rupture = stock_data.is_rupture
        existing_stock.declared_by = current_user.id
        db.commit()
        db.refresh(existing_stock)
        return existing_stock
    else:
        # Créer
        new_stock = PharmacyStock(
            pharmacy_id=pharmacy_id,
            medication_id=stock_data.medication_id,
            quantity=stock_data.quantity,
            is_rupture=stock_data.is_rupture,
            declared_by=current_user.id,
        )
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)
        return new_stock
