"""Tests pour les endpoints patients et traitements"""
from fastapi import status
from pydantic import ValidationError
import pytest
from uuid import uuid4

from app.core.config import settings
from app.models.medication import Medication, MedicationCategory, MedicationDomain
from app.models.patient import PatientTreatment, UnlistedMedicationSubmission
from app.schemas.patient import PatientTreatmentCreate


def _required_survey_responses():
    return {
        "treatment_duration": 1,
        "treatment_start_date": "2025-01-01T00:00:00",
        "treatment_is_ongoing": True,
        "monthly_cost": "prefer-not-to-say",
        "unit_price": "prefer-not-to-say",
        "found_medication": "no",
        "pharmacies_visited": "0",
        "waiting_time": "unknown",
        "stockout_frequency": "unknown",
        "wants_alert": False,
        "morning_pills": "0",
        "noon_pills": "0",
        "evening_pills": "0",
        "education_level": "prefer-not-to-say",
        "minimum_salary": "prefer-not-to-say",
        "employment_status": "prefer-not-to-say",
        "has_financial_resources": "prefer-not-to-say",
        "emotional_impact": "prefer-not-to-say",
        "social_stigma": "prefer-not-to-say",
        "professional_impact": "prefer-not-to-say",
        "social_support": "prefer-not-to-say",
        "access_barrier": "prefer-not-to-say",
        "cost_related_treatment_change": "prefer-not-to-say",
        "discrimination_context": "prefer-not-to-say",
        "rights_support_need": "prefer-not-to-say",
        "has_alternative_medication": False,
        "knows_restock_delay": False,
        "action_when_delay_unknown": "Je vérifie auprès de la pharmacie.",
    }


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
            **_required_survey_responses(),
            **treatment_data,
            "email": email,
            "email_verification_token": verification_token,
            "consent_draft_token": consent_response.json()["consent_draft_token"],
        },
    )
    return final_response


class TestPatientTreatmentCreate:
    """Tests pour POST /patients/treatments"""

    def test_psychosocial_fields_accept_known_categories_and_reject_unknown_values(self):
        treatment_data = {
            "age": 35,
            "sex": "homme",
            "location": "Cotonou",
            "medication_name": "Médicament non répertorié",
            "dosage": "500 mg",
            "frequency": "2 fois par jour",
            "access_ease": "difficile",
            "effectiveness": 8,
            "emotional_impact": "moderate",
            "social_stigma": "sometimes",
            "professional_impact": "major",
            "social_support": "partial",
            "access_barrier": "transport",
            "cost_related_treatment_change": "missed_or_reduced_doses",
            "discrimination_context": "work",
            "rights_support_need": "legal_support",
            "email": "patient@example.com",
            "email_verification_token": "v" * 32,
            "consent_draft_token": "c" * 32,
        }

        model = PatientTreatmentCreate.model_validate({
            **_required_survey_responses(),
            **treatment_data,
        })
        assert model.medication_name == "Médicament non répertorié"
        assert model.emotional_impact == "moderate"
        assert model.cost_related_treatment_change == "missed_or_reduced_doses"
        assert model.discrimination_context == "work"
        assert model.rights_support_need == "legal_support"

        for field_name in (
            "cost_related_treatment_change",
            "discrimination_context",
            "rights_support_need",
        ):
            with pytest.raises(ValidationError):
                PatientTreatmentCreate.model_validate({
                    **_required_survey_responses(),
                    **treatment_data,
                    field_name: "unknown-category",
                })
            incomplete_responses = {
                **_required_survey_responses(),
                **treatment_data,
            }
            incomplete_responses.pop(field_name)
            with pytest.raises(ValidationError):
                PatientTreatmentCreate.model_validate(incomplete_responses)

    def test_create_requires_structured_survey_responses(self):
        treatment_data = {
            "age": 35,
            "sex": "homme",
            "location": "Cotonou",
            "medication_name": "Valproate",
            "dosage": "500 mg",
            "frequency": "2 fois par jour",
            "access_ease": "difficult",
            "effectiveness": 8,
            "email": "patient@example.com",
            "email_verification_token": "v" * 32,
            "consent_draft_token": "c" * 32,
        }

        with pytest.raises(ValidationError):
            PatientTreatmentCreate.model_validate(treatment_data)
    
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
            "cost_related_treatment_change": "stopped_treatment",
            "discrimination_context": "healthcare",
            "rights_support_need": "rights_information",
        }
        response = _create_treatment(client, treatment_data, monkeypatch)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["medication_name"] == "Valproate"
        assert data["age"] == 35
        assert data["name"] == ""
        assert data["cost_related_treatment_change"] == "stopped_treatment"
        assert data["discrimination_context"] == "healthcare"
        assert data["rights_support_need"] == "rights_information"

    def test_create_treatment_with_unlisted_medication_name(self, client, monkeypatch):
        """A medication name outside the predefined frontend list is stored as entered."""
        medication_name = "Médicament non répertorié"
        treatment_data = {
            "age": 35,
            "sex": "homme",
            "location": "Cotonou",
            "medication_name": medication_name,
            "dosage": "500 mg",
            "frequency": "2 fois par jour",
            "access_ease": "difficile",
            "effectiveness": 8,
        }

        response = _create_treatment(client, treatment_data, monkeypatch)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["medication_name"] == medication_name

    def test_unlisted_medication_is_saved_as_pending_proposal_not_catalog_entry(
        self, client, monkeypatch, db_session
    ):
        domain = MedicationDomain(id="mental_health", label="Santé mentale")
        category = MedicationCategory(
            id="antidepresseurs",
            domain=domain,
            label="Antidépresseurs",
        )
        db_session.add_all([domain, category])
        db_session.commit()
        treatment_data = {
            "age": 35,
            "sex": "femme",
            "location": "Cotonou",
            "medication_name": "Nom saisi par la patiente",
            "medication_category_id": "antidepresseurs",
            "medication_is_unlisted": True,
            "medication_country": "Bénin",
            "dosage": "25 mg",
            "frequency": "1 fois par jour",
            "access_ease": "difficile",
            "effectiveness": 6,
        }

        response = _create_treatment(client, treatment_data, monkeypatch)

        assert response.status_code == status.HTTP_201_CREATED
        proposal = response.json()["unlisted_medication_submission"]
        assert proposal["status"] == "pending_validation"
        assert proposal["country"] == "Bénin"
        assert proposal["location"] == "Cotonou"
        assert db_session.query(UnlistedMedicationSubmission).count() == 1
        assert db_session.query(Medication).count() == 0

    def test_unlisted_medication_can_have_unknown_category_but_requires_country(self):
        treatment_data = {
            "age": 35,
            "sex": "femme",
            "location": "Cotonou",
            "medication_name": "Nom saisi par la patiente",
            "medication_is_unlisted": True,
            "medication_category_id": None,
            "medication_country": "Bénin",
            "dosage": "25 mg",
            "frequency": "1 fois par jour",
            "access_ease": "difficile",
            "effectiveness": 6,
            "email": "patient@example.com",
            "email_verification_token": "v" * 32,
            "consent_draft_token": "c" * 32,
        }

        valid = PatientTreatmentCreate.model_validate({
            **_required_survey_responses(),
            **treatment_data,
        })
        assert valid.medication_name == "Nom saisi par la patiente"
        assert valid.medication_country == "Bénin"
        assert valid.medication_category_id is None

        with pytest.raises(ValidationError):
            PatientTreatmentCreate.model_validate({
                **_required_survey_responses(),
                **treatment_data,
                "medication_country": None,
            })


    def test_public_analytics_only_uses_consented_aggregates(self, client, db_session):
        for index in range(11):
            db_session.add(PatientTreatment(
                age=35,
                sex="homme",
                location="Cotonou",
                medication_name="Unlisted medication",
                dosage="500 mg",
                frequency="daily",
                access_ease="easy",
                effectiveness=8,
                consent_analysis=index < 10,
                side_effects="private clinical narrative",
                additional_comments="private identifying narrative",
                contact_email=f"person-{index}@example.com",
            ))
        db_session.commit()

        response = client.get("/api/v1/patients/analytics/public")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sample_size"] == 10
        assert data["breakdowns"]["locations"]["items"] == [
            {"category": "cotonou", "count": 10},
        ]
        assert "side_effects" not in data
        assert "contact_email" not in data
        assert "private clinical narrative" not in response.text
        assert "private identifying narrative" not in response.text
        assert "person-0@example.com" not in response.text

    def test_public_analytics_hides_sample_below_privacy_threshold(self, client, db_session):
        for _ in range(9):
            db_session.add(PatientTreatment(
                age=35,
                sex="homme",
                location="Cotonou",
                medication_name="Valproate",
                dosage="500 mg",
                frequency="daily",
                access_ease="easy",
                effectiveness=8,
                consent_analysis=True,
            ))
        db_session.commit()

        response = client.get("/api/v1/patients/analytics/public")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["sample_size"] is None
        assert response.json()["data_suppressed"] is True
        assert response.json()["breakdowns"] == {}
    
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
