"""Tests for verified-email patient treatment management."""

from uuid import uuid4

from app.core.config import settings


def _request_code(client, email, purpose, sent_codes):
    response = client.post(
        "/api/v1/patients/treatments/email-verification/request",
        json={"email": email, "purpose": purpose},
    )
    assert response.status_code == 202
    return sent_codes[-1][1]


def _verify_code(client, email, purpose, code):
    response = client.post(
        "/api/v1/patients/treatments/email-verification/confirm",
        json={"email": email, "purpose": purpose, "code": code},
    )
    assert response.status_code == 200
    return response.json()


def _consent_and_create(client, email, verification_token, medication):
    consent_response = client.post(
        "/api/v1/patients/treatments/consent",
        json={
            "email": email,
            "email_verification_token": verification_token,
            "consent_analysis": False,
            "consent_alerts": True,
            "consent_text_version": settings.PATIENT_CONSENT_TEXT_VERSION,
        },
    )
    assert consent_response.status_code == 201

    response = client.post(
        "/api/v1/patients/treatments",
        json={
            "age": 34,
            "sex": "non-specifie",
            "location": "Dakar",
            "medication_name": medication,
            "dosage": "500mg",
            "frequency": "1x/jour",
            "access_ease": "difficile",
            "effectiveness": 7,
            "email": email,
            "email_verification_token": verification_token,
            "consent_draft_token": consent_response.json()["consent_draft_token"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_verified_email_can_manage_only_its_treatments_atomically(
    client, monkeypatch
):
    email = f"{uuid4().hex}@example.com"
    sent_codes = []
    monkeypatch.setattr(
        "app.api.v1.patients.send_patient_verification_code",
        lambda sent_email, code, purpose: sent_codes.append((sent_email, code, purpose)),
    )
    registration_code = _request_code(
        client, email, "registration", sent_codes
    )
    registration = _verify_code(
        client, email, "registration", registration_code
    )
    verification_token = registration["verification_token"]

    first = _consent_and_create(client, email, verification_token, "Valproate")
    second = _consent_and_create(client, email, verification_token, "Lamotrigine")
    assert first["email_verified"] is True
    assert first["email_verified_at"] is not None
    assert first["consent_analysis"] is False
    assert first["consent_alerts"] is True
    assert first["consent_text_version"] == settings.PATIENT_CONSENT_TEXT_VERSION
    assert first["consented_at"] < first["consent_confirmed_at"]
    assert "email" not in first

    assert client.get("/api/v1/patients/treatments/mine").status_code == 401
    management_code = _request_code(client, email, "management", sent_codes)
    management = _verify_code(client, email, "management", management_code)
    headers = {"Authorization": f"Bearer {management['session_token']}"}

    listed = client.get("/api/v1/patients/treatments/mine", headers=headers)
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {first["id"], second["id"]}

    updated = client.patch(
        f"/api/v1/patients/treatments/mine/{first['id']}",
        headers=headers,
        json={"dosage": "750mg"},
    )
    assert updated.status_code == 200
    assert updated.json()["dosage"] == "750mg"

    # A mixed owned/unowned batch is rejected without deleting either record.
    rejected_batch = client.request(
        "DELETE",
        "/api/v1/patients/treatments/mine",
        headers=headers,
        json={"treatment_ids": [first["id"], str(uuid4())]},
    )
    assert rejected_batch.status_code == 404
    assert len(client.get("/api/v1/patients/treatments/mine", headers=headers).json()) == 2

    deleted = client.request(
        "DELETE",
        "/api/v1/patients/treatments/mine",
        headers=headers,
        json={"treatment_ids": [first["id"]]},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 1

    withdrawn = client.post(
        "/api/v1/patients/treatments/mine/consent/withdraw",
        headers=headers,
        json={
            "treatment_ids": [second["id"]],
            "confirm_withdrawal": True,
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["deleted_count"] == 1
    assert client.get("/api/v1/patients/treatments/mine", headers=headers).json() == []


def test_consent_requires_current_version_and_alert_consent(client, monkeypatch):
    email = f"{uuid4().hex}@example.com"
    sent_codes = []
    monkeypatch.setattr(
        "app.api.v1.patients.send_patient_verification_code",
        lambda sent_email, code, purpose: sent_codes.append((sent_email, code, purpose)),
    )
    code = _request_code(client, email, "registration", sent_codes)
    verification = _verify_code(client, email, "registration", code)

    data = {
        "email": email,
        "email_verification_token": verification["verification_token"],
        "consent_analysis": False,
        "consent_alerts": True,
        "consent_text_version": "obsolete",
    }
    assert client.post("/api/v1/patients/treatments/consent", json=data).status_code == 409

    data["consent_text_version"] = settings.PATIENT_CONSENT_TEXT_VERSION
    data["consent_alerts"] = False
    assert client.post("/api/v1/patients/treatments/consent", json=data).status_code == 422


def test_management_code_is_generic_for_unknown_email(client, monkeypatch):
    email = f"{uuid4().hex}@example.com"
    sent_codes = []
    monkeypatch.setattr(
        "app.api.v1.patients.send_patient_verification_code",
        lambda sent_email, code, purpose: sent_codes.append((sent_email, code, purpose)),
    )
    response = client.post(
        "/api/v1/patients/treatments/email-verification/request",
        json={"email": email, "purpose": "management"},
    )
    assert response.status_code == 202
    assert response.json() == {
        "message": (
            "Si l'adresse est valide et la demande autorisée, "
            "un code de vérification sera envoyé."
        )
    }
    verified = _verify_code(client, email, "management", sent_codes[-1][1])
    assert client.get(
        "/api/v1/patients/treatments/mine",
        headers={"Authorization": f"Bearer {verified['session_token']}"},
    ).json() == []
