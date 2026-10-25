"""Tests pour les endpoints patients et traitements"""
from fastapi import status
from uuid import uuid4

from app.core.config import settings


def _create_treatment(client, treatment_data, monkeypatch, email=None, verification_token=None):
    email = email or f"{uuid4().hex}@example.com"
    sent_codes = []
    monkeypatch.setattr(
        "app.api.v1.patients.send_patient_verification_code",
        lambda sent_email, code, purpose: sent_codes.append((sent_email, code, purpose)),
    )

    if verification_token is None:
        request_response = client.post(
            "/api/v1/patients/treatments/email-verification/request",
            json={"email": email, "purpose": "registration"},
        )
        assert request_response.status_code == status.HTTP_202_ACCEPTED
        assert request_response.json() == {
            "message": (
                "Si l'adresse est valide et la demande autorisée, "
                "un code de vérification sera envoyé."
            )
        }

        verification_response = client.post(
            "/api/v1/patients/treatments/email-verification/confirm",
            json={
                "email": email,
                "purpose": "registration",
                "code": sent_codes[-1][1],
            },
        )
        assert verification_response.status_code == status.HTTP_200_OK
        verification_token = verification_response.json()["verification_token"]

    consent_response = client.post(
        "/api/v1/patients/treatments/consent",
        json={
            "email": email,
            "email_verification_token": verification_token,
            "consent_analysis": True,
            "consent_alerts": True,
            "consent_text_version": settings.PATIENT_CONSENT_TEXT_VERSION,
        },
    )
    assert consent_response.status_code == status.HTTP_201_CREATED

    final_response = client.post(
        "/api/v1/patients/treatments",
        json={
            **treatment_data,
            "email": email,
            "email_verification_token": verification_token,
            "consent_draft_token": consent_response.json()["consent_draft_token"],
        },
    )
    return final_response


class TestPatientTreatmentCreate:
    """Tests pour POST /patients/treatments"""
    
    def test_create_treatment_anonymous(self, client, monkeypatch):
        """Test création traitement anonyme (sans JWT)"""
        treatment_data = {
            "name": "John",
            "age": 35,
            "sex": "homme",
            "location": "Dakar",
            "medication_name": "Valproate",
            "dosage": "500mg",
            "frequency": "2x/jour",
            "access_ease": "difficile",
            "effectiveness": 8,
        }
        response = _create_treatment(client, treatment_data, monkeypatch)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["medication_name"] == "Valproate"
        assert data["age"] == 35
        assert data["name"] == ""
    
    def test_create_treatment_with_duration(self, client, monkeypatch):
        """Test création traitement avec durée"""
        treatment_data = {
            "age": 42,
            "sex": "femme",
            "location": "Casablanca",
            "medication_name": "Lamotrigine",
            "dosage": "200mg",
            "frequency": "1x/jour",
            "treatment_duration": 12,
            "access_ease": "facile",
            "effectiveness": 9,
        }
        response = _create_treatment(client, treatment_data, monkeypatch)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["treatment_duration"] == 12
    
    def test_create_treatment_invalid_age(self, client):
        """Test création avec âge invalide (< 0 ou > 150)"""
        treatment_data = {
            "age": 200,  # Invalid
            "sex": "homme",
            "location": "Dakar",
            "medication_name": "Valproate",
            "dosage": "500mg",
            "frequency": "2x/jour",
            "access_ease": "difficile",
            "effectiveness": 8,
        }
        response = client.post(
            "/api/v1/patients/treatments",
            json=treatment_data,
        )
        # Pydantic validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_treatment_invalid_effectiveness(self, client):
        """Test création avec effectivité invalide (< 1 ou > 10)"""
        treatment_data = {
            "age": 35,
            "sex": "homme",
            "location": "Dakar",
            "medication_name": "Valproate",
            "dosage": "500mg",
            "frequency": "2x/jour",
            "access_ease": "difficile",
            "effectiveness": 15,  # Invalid
        }
        response = client.post(
            "/api/v1/patients/treatments",
            json=treatment_data,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_treatment_with_optional_fields(self, client, monkeypatch):
        """Test création traitement avec champs optionnels"""
        treatment_data = {
            "age": 50,
            "sex": "autre",
            "location": "Lagos",
            "medication_name": "Phenobarbital",
            "dosage": "100mg",
            "frequency": "2x/jour",
            "access_ease": "moyen",
            "effectiveness": 7,
            "side_effects": "Somnolence légère",
            "difficulties": "Coût élevé",
            "additional_comments": "Bon résultat général",
            "wants_alert": True,
        }
        response = _create_treatment(client, treatment_data, monkeypatch)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["side_effects"] == "Somnolence légère"
        assert data["wants_alert"] == True


class TestPatientTreatmentList:
    """Tests pour GET /patients/treatments"""
    
    def test_list_treatments_empty(self, client, admin_auth_headers):
        """Test lister traitements quand aucun"""
        response = client.get(
            "/api/v1/patients/treatments",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_treatments_with_data(self, client, monkeypatch, admin_auth_headers):
        """Test lister traitements avec données"""
        # Créer un traitement
        treatment_data = {
            "age": 30,
            "sex": "homme",
            "location": "Ouagadougou",
            "medication_name": "Levetiracetam",
            "dosage": "500mg",
            "frequency": "2x/jour",
            "access_ease": "facile",
            "effectiveness": 8,
        }
        created = _create_treatment(client, treatment_data, monkeypatch)
        assert created.status_code == status.HTTP_201_CREATED
        
        # Lister
        response = client.get(
            "/api/v1/patients/treatments",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert data[0]["medication_name"] == "Levetiracetam"
    
    def test_list_treatments_without_personal_data_filters(self, client, monkeypatch, admin_auth_headers):
        """Admin listing does not filter declarations by city or medication."""
        # Créer traitements
        first = _create_treatment(client, {
            "age": 30, "sex": "homme", "location": "Dakar",
            "medication_name": "Valproate", "dosage": "500mg",
            "frequency": "2x/jour", "access_ease": "difficile", "effectiveness": 8,
        }, monkeypatch)
        second = _create_treatment(client, {
            "age": 25, "sex": "femme", "location": "Lagos",
            "medication_name": "Lamotrigine", "dosage": "200mg",
            "frequency": "1x/jour", "access_ease": "facile", "effectiveness": 9,
        }, monkeypatch)
        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_201_CREATED

        response = client.get(
            "/api/v1/patients/treatments",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert {t["medication_name"] for t in data} == {"Valproate", "Lamotrigine"}


class TestPatientTreatmentStats:
    """Tests pour GET /patients/treatments/stats"""
    
    def test_get_stats_empty(self, client, admin_auth_headers):
        """Test stats quand aucun traitement"""
        response = client.get(
            "/api/v1/patients/treatments/stats",
            headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_treatments"] == 0
    
    def test_get_stats_with_data(self, client, monkeypatch, admin_auth_headers):
        """Test stats avec données"""
        # Créer traitements
        for i in range(3):
            response = _create_treatment(client, {
                "age": 30 + i,
                "sex": "homme",
                "location": "Dakar",
                "medication_name": "Valproate",
                "dosage": "500mg",
                "frequency": "2x/jour",
                "access_ease": "difficile",
                "effectiveness": 7 + i,  # 7, 8, 9
            }, monkeypatch)
            assert response.status_code == status.HTTP_201_CREATED

        response = client.get(
            "/api/v1/patients/treatments/stats",
            headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_treatments"] == 3
        assert "average_effectiveness" in data
        assert "common_medications" in data
