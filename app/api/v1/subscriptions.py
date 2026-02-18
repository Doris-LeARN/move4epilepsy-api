"""
Endpoints pour les abonnements pharmacies
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.database.base import get_db
from app.models.subscription import SubscriptionPlan, PharmacySubscription, SubscriptionPayment
from app.models.pharmacy import Pharmacy
from app.schemas.subscription import (
    SubscriptionPlanResponse, SubscriptionPlanCreate,
    PharmacySubscriptionResponse, PharmacySubscriptionCreate,
    SubscriptionPaymentResponse, SubscriptionPaymentCreate
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_pharmacien, require_admin

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    country: Optional[str] = Query(None, description="Filtrer par pays"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Récupère les plans d'abonnement (public)"""
    query = db.query(SubscriptionPlan)
    
    if active_only:
        query = query.filter(SubscriptionPlan.is_active == True)
    
    if country:
        query = query.filter(SubscriptionPlan.country == country)
    
    plans = query.order_by(SubscriptionPlan.monthly_price).all()
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupère un plan par son ID"""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    return plan


@router.get("/my-subscription", response_model=Optional[PharmacySubscriptionResponse])
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_pharmacien),
    db: Session = Depends(get_db)
):
    """Récupère l'abonnement de la pharmacie de l'utilisateur"""
    # Trouver la pharmacie de l'utilisateur
    pharmacy = db.query(Pharmacy).filter(Pharmacy.user_id == current_user.id).first()
    
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found for this user"
        )
    
    subscription = db.query(PharmacySubscription).filter(
        PharmacySubscription.pharmacy_id == pharmacy.id
    ).order_by(PharmacySubscription.created_at.desc()).first()
    
    return subscription


@router.post("/subscribe", response_model=PharmacySubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    subscription_data: PharmacySubscriptionCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_pharmacien),
    db: Session = Depends(get_db)
):
    """S'abonner à un plan (pharmacien uniquement)"""
    # Vérifier que le plan existe
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription_data.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Trouver la pharmacie de l'utilisateur
    pharmacy = db.query(Pharmacy).filter(Pharmacy.user_id == current_user.id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found for this user"
        )
    
    # Vérifier s'il y a déjà un abonnement actif
    existing = db.query(PharmacySubscription).filter(
        PharmacySubscription.pharmacy_id == pharmacy.id,
        PharmacySubscription.status.in_(["active", "trial"])
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription"
        )
    
    # Créer l'abonnement (trial de 30 jours)
    end_date = datetime.utcnow() + timedelta(days=30)
    
    subscription = PharmacySubscription(
        pharmacy_id=pharmacy.id,
        plan_id=subscription_data.plan_id,
        status="trial",
        start_date=datetime.utcnow(),
        end_date=end_date,
        auto_renew=subscription_data.auto_renew,
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.post("/payments", response_model=SubscriptionPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: SubscriptionPaymentCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_pharmacien),
    db: Session = Depends(get_db)
):
    """Enregistre un paiement (pharmacien uniquement)"""
    # Vérifier que l'abonnement existe
    subscription = db.query(PharmacySubscription).filter(
        PharmacySubscription.id == payment_data.subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Vérifier que c'est l'abonnement de la pharmacie de l'utilisateur
    pharmacy = db.query(Pharmacy).filter(Pharmacy.user_id == current_user.id).first()
    if pharmacy and subscription.pharmacy_id != pharmacy.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create payments for your own subscription"
        )
    
    # Créer le paiement
    payment = SubscriptionPayment(
        subscription_id=payment_data.subscription_id,
        pharmacy_id=subscription.pharmacy_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        payment_provider=payment_data.payment_provider,
        transaction_id=payment_data.transaction_id,
        status="pending",
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return payment


@router.put("/payments/{payment_id}/complete", response_model=SubscriptionPaymentResponse)
async def complete_payment(
    payment_id: UUID,
    transaction_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Marque un paiement comme complété (admin uniquement)"""
    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment.status = "completed"
    payment.paid_at = datetime.utcnow()
    
    if transaction_id:
        payment.transaction_id = transaction_id
    
    # Activer l'abonnement associé
    if payment.subscription_id:
        subscription = db.query(PharmacySubscription).filter(
            PharmacySubscription.id == payment.subscription_id
        ).first()
        if subscription:
            subscription.status = "active"
            # Prolonger l'abonnement d'un mois
            subscription.end_date = datetime.utcnow() + timedelta(days=30)
    
    db.commit()
    db.refresh(payment)
    
    return payment


@router.post("/plans", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crée un plan d'abonnement (admin uniquement)"""
    plan = SubscriptionPlan(**plan_data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return plan
