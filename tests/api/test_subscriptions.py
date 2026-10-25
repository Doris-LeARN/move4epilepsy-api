"""Tests for pharmacy subscription checkout."""

from decimal import Decimal

from app.models.pharmacy import Pharmacy
from app.models.subscription import SubscriptionPlan


def _create_pharmacist_and_plan(db_session, test_user):
    test_user.profile.role = "pharmacien"
    pharmacy = Pharmacy(
        pharmacy_id="PHARMACY-TEST",
        name="Pharmacie de test",
        license_number="LICENSE-TEST",
        address="1 rue de test",
        city="Cotonou",
        department="Littoral",
        commune="Cotonou",
        responsible_first_name="Test",
        responsible_last_name="Pharmacien",
        user_id=test_user.id,
    )
    plan = SubscriptionPlan(
        name="Essentiel",
        country="Bénin",
        monthly_price=Decimal("10.00"),
        annual_price=Decimal("100.00"),
        currency="XOF",
        features=["professional_profile"],
        is_active=True,
    )
    db_session.add_all([pharmacy, plan])
    db_session.commit()
    db_session.refresh(plan)
    return pharmacy, plan


def test_public_plan_list_only_returns_active_plans_for_country(client, db_session):
    active_plan = SubscriptionPlan(
        name="Essentiel",
        country="Bénin",
        monthly_price=Decimal("10.00"),
        annual_price=Decimal("100.00"),
        currency="XOF",
        is_active=True,
    )
    inactive_plan = SubscriptionPlan(
        name="Ancienne offre",
        country="Bénin",
        monthly_price=Decimal("5.00"),
        annual_price=Decimal("50.00"),
        currency="XOF",
        is_active=False,
    )
    db_session.add_all([active_plan, inactive_plan])
    db_session.commit()

    response = client.get("/api/v1/subscriptions/plans?country=b%C3%A9nin")

    assert response.status_code == 200
    assert [plan["name"] for plan in response.json()] == ["Essentiel"]


def test_subscription_uses_server_price_and_stays_pending_until_paid(
    client, db_session, test_user, auth_headers
):
    _, plan = _create_pharmacist_and_plan(db_session, test_user)

    response = client.post(
        "/api/v1/subscriptions/subscribe",
        headers=auth_headers,
        json={
            "plan_id": str(plan.id),
            "billing_country": "Bénin",
            "billing_period": "annual",
        },
    )

    assert response.status_code == 201
    subscription = response.json()
    assert subscription["status"] == "pending_payment"
    assert subscription["billing_country"] == "Bénin"
    assert subscription["billing_period"] == "annual"
    assert subscription["amount"] == "100.00"
    assert subscription["currency"] == "XOF"

    forged_payment = client.post(
        "/api/v1/subscriptions/payments",
        headers=auth_headers,
        json={
            "subscription_id": subscription["id"],
            "payment_method": "card",
            "amount": "1.00",
            "currency": "XOF",
        },
    )
    assert forged_payment.status_code == 400

    payment = client.post(
        "/api/v1/subscriptions/payments",
        headers=auth_headers,
        json={
            "subscription_id": subscription["id"],
            "payment_method": "card",
        },
    )
    assert payment.status_code == 201
    assert payment.json()["amount"] == "100.00"
    assert payment.json()["currency"] == "XOF"

    repeated_payment = client.post(
        "/api/v1/subscriptions/payments",
        headers=auth_headers,
        json={
            "subscription_id": subscription["id"],
            "payment_method": "card",
        },
    )
    assert repeated_payment.status_code == 201
    assert repeated_payment.json()["id"] == payment.json()["id"]

    different_method = client.post(
        "/api/v1/subscriptions/payments",
        headers=auth_headers,
        json={
            "subscription_id": subscription["id"],
            "payment_method": "mobile_money",
        },
    )
    assert different_method.status_code == 409


def test_subscription_rejects_plan_from_another_billing_country(
    client, db_session, test_user, auth_headers
):
    _, plan = _create_pharmacist_and_plan(db_session, test_user)

    response = client.post(
        "/api/v1/subscriptions/subscribe",
        headers=auth_headers,
        json={
            "plan_id": str(plan.id),
            "billing_country": "France",
            "billing_period": "monthly",
        },
    )

    assert response.status_code == 400
