"""
Endpoints pour les abonnements pharmacies
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from calendar import monthrange
from decimal import Decimal
from sqlalchemy import func
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


def _billing_period_end(start: datetime, billing_period: str) -> datetime:
    months = 12 if billing_period == "annual" else 1
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    country: Optional[str] = Query(None, description="Filtrer par pays"),
    db: Session = Depends(get_db)
):
    """Récupère les plans d'abonnement (public)"""
    query = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active.is_(True),
        SubscriptionPlan.monthly_price > 0,
        SubscriptionPlan.annual_price > 0,
    )
    
    if country:
        query = query.filter(func.lower(SubscriptionPlan.country) == country.strip().lower())
    
    plans = query.order_by(SubscriptionPlan.monthly_price).all()
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupère un plan par son ID"""
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active.is_(True),
        SubscriptionPlan.monthly_price > 0,
        SubscriptionPlan.annual_price > 0,
    ).first()
    
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
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription_data.plan_id,
        SubscriptionPlan.is_active.is_(True),
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )

    if plan.country.strip().lower() != subscription_data.billing_country.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected plan is not available for the billing country"
        )

    amount = (
        plan.annual_price
        if subscription_data.billing_period == "annual"
        else plan.monthly_price
    )
    if amount is None or amount <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected billing period is not configured for this plan"
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
        PharmacySubscription.status.in_(["active", "trial", "pending_payment"])
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription or a pending checkout"
        )
    
    # Keep the subscription pending until payment confirmation.
    now = datetime.now(timezone.utc)
    end_date = _billing_period_end(now, subscription_data.billing_period)

    subscription = PharmacySubscription(
        pharmacy_id=pharmacy.id,
        plan_id=subscription_data.plan_id,
        status="pending_payment",
        start_date=now,
        end_date=end_date,
        auto_renew=subscription_data.auto_renew,
        billing_country=subscription_data.billing_country.strip(),
        billing_period=subscription_data.billing_period,
        amount=amount,
        currency=plan.currency,
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
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found for this user"
        )
    if subscription.pharmacy_id != pharmacy.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create payments for your own subscription"
        )

    if subscription.amount is None or not subscription.currency:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The subscription has no confirmed price"
        )
    if subscription.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subscription is not awaiting payment"
        )
    if payment_data.amount is not None and payment_data.amount != subscription.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount does not match the subscription price"
        )
    if payment_data.currency is not None and payment_data.currency.upper() != subscription.currency.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment currency does not match the subscription price"
        )

    existing_payment = db.query(SubscriptionPayment).filter(
        SubscriptionPayment.subscription_id == subscription.id,
        SubscriptionPayment.status == "pending",
    ).first()
    if existing_payment:
        if (
            existing_payment.payment_method != payment_data.payment_method
            or existing_payment.payment_provider != payment_data.payment_provider
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending payment already exists with another payment method"
            )
        return existing_payment

    # Créer le paiement
    payment = SubscriptionPayment(
        subscription_id=payment_data.subscription_id,
        pharmacy_id=subscription.pharmacy_id,
        amount=subscription.amount,
        currency=subscription.currency,
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
    
    if payment.status == "completed":
        return payment
    if payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending payments can be completed"
        )

    payment.status = "completed"
    payment.paid_at = datetime.now(timezone.utc)
    
    if transaction_id:
        payment.transaction_id = transaction_id
    
    # Activer l'abonnement associé
    if payment.subscription_id:
        subscription = db.query(PharmacySubscription).filter(
            PharmacySubscription.id == payment.subscription_id
        ).first()
        if subscription:
            subscription.status = "active"
            subscription.start_date = payment.paid_at
            subscription.end_date = _billing_period_end(
                payment.paid_at,
                subscription.billing_period,
            )
    
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
