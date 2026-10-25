from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import pharmacies
from app.core.email import EmailDeliveryError
from app.database.base import Base
from app.models.patient import PatientAvailabilityNotification, PatientTreatment


@pytest.mark.parametrize(
    ("previous_quantity", "previous_rupture", "quantity", "rupture", "expected"),
    [
        (0, False, 4, False, True),
        (4, False, 7, False, False),
        (0, False, 0, False, False),
        (4, True, 4, False, True),
        (4, False, 4, True, False),
    ],
)
def test_availability_event_only_tracks_unavailable_to_available(
    previous_quantity,
    previous_rupture,
    quantity,
    rupture,
    expected,
):
    assert pharmacies._availability_restored(
        previous_quantity,
        previous_rupture,
        quantity,
        rupture,
    ) is expected


@pytest.fixture
def alert_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            PatientTreatment.__table__,
            PatientAvailabilityNotification.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _treatment(email, location="Dakar", consent_alerts=True):
    return PatientTreatment(
        age=34,
        sex="non-specifie",
        location=location,
        medication_name="Valproate",
        dosage="500mg",
        frequency="1x/jour",
        access_ease="difficile",
        effectiveness=7,
        wants_alert=True,
        contact_email=email,
        email_verified=True,
        consent_alerts=consent_alerts,
    )


def _stock():
    return SimpleNamespace(id=uuid4(), availability_version=1)


def test_matching_alert_is_sent_once_per_availability_event(alert_db, monkeypatch):
    alert_db.add_all([
        _treatment("matching@example.com"),
        _treatment("no-consent@example.com", consent_alerts=False),
        _treatment("other-location@example.com", location="Thiès"),
    ])
    alert_db.commit()
    sent_to = []
    monkeypatch.setattr(
        pharmacies,
        "send_patient_availability_alert",
        sent_to.append,
    )
    stock = _stock()
    pharmacy = SimpleNamespace(city="Dakar", commune="Plateau", department="Dakar")
    medication = SimpleNamespace(name="Valproate")

    pharmacies._queue_patient_availability_alerts(
        alert_db, stock, pharmacy, medication
    )
    alert_db.commit()
    pharmacies._deliver_pending_patient_alerts(alert_db, stock)
    pharmacies._queue_patient_availability_alerts(
        alert_db, stock, pharmacy, medication
    )
    alert_db.commit()
    pharmacies._deliver_pending_patient_alerts(alert_db, stock)

    notifications = alert_db.query(PatientAvailabilityNotification).all()
    assert sent_to == ["matching@example.com"]
    assert len(notifications) == 1
    assert notifications[0].status == "sent"
    assert notifications[0].availability_version == stock.availability_version


def test_failed_alert_remains_pending_and_can_be_retried(alert_db, monkeypatch):
    alert_db.add(_treatment("retry@example.com"))
    alert_db.commit()
    stock = _stock()
    pharmacy = SimpleNamespace(city="Dakar", commune="Plateau", department="Dakar")
    medication = SimpleNamespace(name="Valproate")

    def fail_delivery(email):
        assert email == "retry@example.com"
        raise EmailDeliveryError("SMTP unavailable")

    monkeypatch.setattr(pharmacies, "send_patient_availability_alert", fail_delivery)
    pharmacies._queue_patient_availability_alerts(
        alert_db, stock, pharmacy, medication
    )
    alert_db.commit()
    with pytest.raises(HTTPException) as error:
        pharmacies._deliver_pending_patient_alerts(alert_db, stock)
    assert error.value.status_code == 503

    notification = alert_db.query(PatientAvailabilityNotification).one()
    assert notification.status == "pending"
    assert notification.attempts == 1

    sent_to = []
    monkeypatch.setattr(
        pharmacies,
        "send_patient_availability_alert",
        sent_to.append,
    )
    pharmacies._deliver_pending_patient_alerts(alert_db, stock)
    alert_db.refresh(notification)

    assert sent_to == ["retry@example.com"]
    assert notification.status == "sent"
    assert notification.attempts == 1
