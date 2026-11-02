from fastapi import status

from app.models.medication import Medication
from app.models.pharmacy import Pharmacy, PharmacyStock


def _login(client):
    return client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )


def test_pharmacy_analytics_is_scoped_to_linked_pharmacy(client, db_session, test_user):
    test_user.profile.role = "pharmacien"
    own_pharmacy = Pharmacy(
        pharmacy_id="PHARMACY-OWN",
        name="Own pharmacy",
        license_number="OWN-001",
        address="Main street",
        city="Cotonou",
        department="Littoral",
        commune="Cotonou",
        responsible_first_name="Test",
        responsible_last_name="Pharmacist",
        user_id=test_user.id,
    )
    other_pharmacy = Pharmacy(
        pharmacy_id="PHARMACY-OTHER",
        name="Other pharmacy",
        license_number="OTHER-001",
        address="Other street",
        city="Abomey-Calavi",
        department="Atlantique",
        commune="Abomey-Calavi",
        responsible_first_name="Other",
        responsible_last_name="Pharmacist",
    )
    medication = Medication(name="Valproate", dosage="500 mg")
    db_session.add_all([own_pharmacy, other_pharmacy, medication])
    db_session.flush()
    db_session.add_all([
        PharmacyStock(
            pharmacy_id=own_pharmacy.id,
            medication_id=medication.id,
            quantity=5,
            is_rupture=False,
        ),
        PharmacyStock(
            pharmacy_id=other_pharmacy.id,
            medication_id=medication.id,
            quantity=0,
            is_rupture=True,
        ),
    ])
    db_session.commit()
    assert _login(client).status_code == status.HTTP_200_OK

    response = client.get("/api/v1/pharmacies/analytics/mine")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["pharmacy_name"] == "Own pharmacy"
    assert data["stock_lines"] == 1
    assert data["total_units"] == 5
    assert data["status_counts"] == {
        "available": 1,
        "low_stock": 0,
        "out_of_stock": 0,
    }


def test_pharmacy_analytics_rejects_non_pharmacist(client, test_user):
    assert _login(client).status_code == status.HTTP_200_OK

    response = client.get("/api/v1/pharmacies/analytics/mine")

    assert response.status_code == status.HTTP_403_FORBIDDEN
