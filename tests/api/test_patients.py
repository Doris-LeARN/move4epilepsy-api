"""Tests pour les endpoints patients et traitements"""
import pytest
from fastapi import status
from datetime import datetime


class TestPatientTreatmentCreate:
    """Tests pour POST /patients/treatments"""
    
    def test_create_treatment_anonymous(self, client):
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
        response = client.post(
            "/api/v1/patients/treatments",
            json=treatment_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["medication_name"] == "Valproate"
        assert data["age"] == 35
    
    def test_create_treatment_with_duration(self, client):
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
        response = client.post(
            "/api/v1/patients/treatments",
            json=treatment_data
        )
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
            json=treatment_data
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
            json=treatment_data
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_treatment_with_optional_fields(self, client):
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
        response = client.post(
            "/api/v1/patients/treatments",
            json=treatment_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["side_effects"] == "Somnolence légère"
        assert data["wants_alert"] == True


class TestPatientTreatmentList:
    """Tests pour GET /patients/treatments"""
    
    def test_list_treatments_empty(self, client):
        """Test lister traitements quand aucun"""
        response = client.get("/api/v1/patients/treatments")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_treatments_with_data(self, client):
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
        client.post("/api/v1/patients/treatments", json=treatment_data)
        
        # Lister
        response = client.get("/api/v1/patients/treatments")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert data[0]["medication_name"] == "Levetiracetam"
    
    def test_list_treatments_with_filters(self, client):
        """Test lister avec filtres (location, medication)"""
        # Créer traitements
        client.post("/api/v1/patients/treatments", json={
            "age": 30, "sex": "homme", "location": "Dakar",
            "medication_name": "Valproate", "dosage": "500mg",
            "frequency": "2x/jour", "access_ease": "difficile", "effectiveness": 8,
        })
        client.post("/api/v1/patients/treatments", json={
            "age": 25, "sex": "femme", "location": "Lagos",
            "medication_name": "Lamotrigine", "dosage": "200mg",
            "frequency": "1x/jour", "access_ease": "facile", "effectiveness": 9,
        })
        
        # Filtrer par location
        response = client.get("/api/v1/patients/treatments?location=Dakar")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(t["location"] == "Dakar" for t in data)


class TestPatientTreatmentStats:
    """Tests pour GET /patients/treatments/stats"""
    
    def test_get_stats_empty(self, client, auth_headers):
        """Test stats quand aucun traitement"""
        response = client.get(
            "/api/v1/patients/treatments/stats",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_treatments"] == 0
    
    def test_get_stats_with_data(self, client, auth_headers):
        """Test stats avec données"""
        # Créer traitements
        for i in range(3):
            client.post("/api/v1/patients/treatments", json={
                "age": 30 + i,
                "sex": "homme",
                "location": "Dakar",
                "medication_name": "Valproate",
                "dosage": "500mg",
                "frequency": "2x/jour",
                "access_ease": "difficile",
                "effectiveness": 7 + i,  # 7, 8, 9
            })
        
        response = client.get(
            "/api/v1/patients/treatments/stats",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_treatments"] == 3
        assert "average_effectiveness" in data
        assert "common_medications" in data
