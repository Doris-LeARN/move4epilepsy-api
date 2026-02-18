"""
Endpoints pour les médicaments
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database.base import get_db
from app.models.medication import Medication
from app.schemas.medication import MedicationResponse, MedicationCreate, MedicationUpdate
from app.schemas.search import SearchParams, SearchResult
from app.core.permissions import require_admin
from app.models.pharmacy import Pharmacy, PharmacyStock
from app.models.patient import PatientSearch
from datetime import datetime

router = APIRouter()


@router.get("", response_model=List[MedicationResponse])
async def get_medications(
    active_only: bool = Query(True, description="Retourner uniquement les médicaments actifs"),
    db: Session = Depends(get_db)
):
    """Récupère tous les médicaments (actifs par défaut)"""
    query = db.query(Medication)
    
    if active_only:
        query = query.filter(Medication.active == True)
    
    medications = query.order_by(Medication.name, Medication.dosage).all()
    return medications


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupère un médicament par son ID"""
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    return medication


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    medication_data: MedicationCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Crée un nouveau médicament (admin uniquement)"""
    # Vérifier si le médicament existe déjà
    existing = db.query(Medication).filter(
        Medication.name == medication_data.name,
        Medication.dosage == medication_data.dosage
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medication with this name and dosage already exists"
        )
    
    medication = Medication(**medication_data.model_dump())
    db.add(medication)
    db.commit()
    db.refresh(medication)
    
    return medication


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: UUID,
    medication_data: MedicationUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Met à jour un médicament (admin uniquement)"""
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    # Mettre à jour les champs fournis
    update_data = medication_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medication, field, value)
    
    db.commit()
    db.refresh(medication)
    
    return medication


@router.post("/search", response_model=List[SearchResult])
async def search_medications(
    params: SearchParams,
    db: Session = Depends(get_db)
):
    """
    Recherche des pharmacies ayant un médicament disponible dans une zone
    
    Enregistre également la recherche pour analytics
    """
    from app.schemas.search import PharmacyInfo, StockInfo
    
    # Vérifier que le médicament existe
    medication = db.query(Medication).filter(Medication.id == params.medication_id).first()
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    # Construire la requête pour trouver les pharmacies dans la zone
    pharmacy_query = db.query(Pharmacy).filter(
        Pharmacy.active == True,
        Pharmacy.department == params.department
    )
    
    if params.commune:
        pharmacy_query = pharmacy_query.filter(Pharmacy.commune == params.commune)
    if params.arrondissement:
        pharmacy_query = pharmacy_query.filter(Pharmacy.arrondissement == params.arrondissement)
    if params.quartier:
        pharmacy_query = pharmacy_query.filter(Pharmacy.quartier == params.quartier)
    
    pharmacies = pharmacy_query.all()
    
    # Pour chaque pharmacie, vérifier le stock
    results = []
    found_count = 0
    
    for pharmacy in pharmacies:
        # Récupérer le stock pour ce médicament
        stock = db.query(PharmacyStock).filter(
            PharmacyStock.pharmacy_id == pharmacy.id,
            PharmacyStock.medication_id == params.medication_id
        ).first()
        
        if stock:
            # Déterminer la disponibilité
            if stock.quantity > 0 and not stock.is_rupture:
                availability = "disponible"
                found_count += 1
            elif stock.is_rupture:
                availability = "indisponible"
            else:
                availability = "non-confirme"
        else:
            availability = "non-confirme"
        
        # Construire le résultat
        result = SearchResult(
            pharmacy=PharmacyInfo(
                id=pharmacy.id,
                name=pharmacy.name,
                address=pharmacy.address,
                phone=pharmacy.phone,
                department=pharmacy.department,
                commune=pharmacy.commune,
                arrondissement=pharmacy.arrondissement,
                quartier=pharmacy.quartier,
            ),
            stock=StockInfo(
                quantity=stock.quantity if stock else 0,
                is_rupture=stock.is_rupture if stock else True,
                last_update=stock.last_update if stock else datetime.utcnow(),
            ),
            availability=availability
        )
        results.append(result)
    
    # Enregistrer la recherche pour analytics
    try:
        search_record = PatientSearch(
            medication_id=params.medication_id,
            department=params.department,
            commune=params.commune,
            arrondissement=params.arrondissement,
            quartier=params.quartier,
            found_results=found_count,
        )
        db.add(search_record)
        db.commit()
    except Exception as e:
        # Ne pas faire échouer la recherche si l'enregistrement échoue
        db.rollback()
        print(f"Erreur lors de l'enregistrement de la recherche: {e}")
    
    return results
