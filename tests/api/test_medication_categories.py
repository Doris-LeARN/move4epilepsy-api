import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.medications import get_medication_categories
from app.database.base import Base
from app.main import app
from app.models.medication import MedicationCategory, MedicationDomain
from app.models.patient import UnlistedMedicationSubmission
from app.schemas.medication import MedicationCategoryResponse
from app.schemas.patient import PatientTreatmentCreate
from scripts.migrate_medication_categories import CATEGORIES, DOMAINS


def test_category_reference_route_is_exposed():
    assert "/api/v1/medications/categories" in app.openapi()["paths"]


def test_reference_contains_specified_domains_and_categories():
    assert {domain_id for domain_id, _ in DOMAINS} == {
        "epilepsy",
        "mental_health",
    }
    assert {category_id for category_id, _, _ in CATEGORIES} == {
        "antiepileptiques",
        "antidepresseurs",
        "anxiolytiques",
        "antipsychotiques",
    }
    assert all(
        domain_id in {key for key, _ in DOMAINS}
        for _, domain_id, _ in CATEGORIES
    )


def test_category_endpoint_returns_categories_with_domain():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            MedicationDomain.__table__,
            MedicationCategory.__table__,
        ],
    )
    try:
        with Session(engine) as session:
            domain = MedicationDomain(id="epilepsy", label="Épilepsie")
            category = MedicationCategory(
                id="antiepileptiques",
                domain=domain,
                label="Antiépileptiques",
            )
            session.add_all([domain, category])
            session.commit()

            results = asyncio.run(get_medication_categories(session))
            response = MedicationCategoryResponse.model_validate(results[0])

            assert response.id == "antiepileptiques"
            assert response.domain.id == "epilepsy"
    finally:
        engine.dispose()


def test_patient_treatment_category_is_optional_for_existing_clients():
    treatment = PatientTreatmentCreate.model_validate({
        "age": 35,
        "sex": "homme",
        "location": "Cotonou",
        "medication_name": "Médicament existant",
        "dosage": "500 mg",
        "frequency": "2 fois par jour",
        "access_ease": "difficile",
        "effectiveness": 8,
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
        "email": "patient@example.com",
        "email_verification_token": "v" * 32,
        "consent_draft_token": "c" * 32,
    })
    assert treatment.medication_category_id is None


def test_unlisted_medication_proposals_have_a_separate_persistence_table():
    assert UnlistedMedicationSubmission.__tablename__ == "unlisted_medication_submissions"
    assert "treatment_id" in UnlistedMedicationSubmission.__table__.c
    assert "country" in UnlistedMedicationSubmission.__table__.c
    assert UnlistedMedicationSubmission.__table__.c.status.default.arg == "pending_validation"
