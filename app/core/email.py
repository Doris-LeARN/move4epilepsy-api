"""SMTP email delivery helpers."""

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    """Raised when the configured email provider cannot deliver a message."""


def send_patient_verification_code(email: str, code: str, purpose: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise EmailDeliveryError("Patient verification email is not configured")

    message = EmailMessage()
    message["Subject"] = "Code de vérification Move4Epilepsy"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    requested_action = (
        "créer une déclaration de traitement"
        if purpose == "registration"
        else "accéder à vos déclarations"
    )
    message.set_content(
        f"Votre code temporaire pour {requested_action} sur Move4Epilepsy est : "
        f"{code}\n\n"
        "Ce code expire dans 10 minutes et ne peut être utilisé qu'une seule fois. "
        "Ne le communiquez à personne.\n\n"
        "Si vous n'avez pas demandé ce code, ignorez ce message."
    )

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as smtp:
            if settings.SMTP_USE_STARTTLS:
                smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("Unable to deliver patient verification email") from error


def send_patient_availability_alert(email: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise EmailDeliveryError("Availability alert email is not configured")

    message = EmailMessage()
    message["Subject"] = "Nouvelle disponibilité sur Move4Epilepsy"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message.set_content(
        "Une pharmacie correspondant à vos critères a signalé un retour en stock. "
        "Consultez Move4Epilepsy pour vérifier les informations avant de vous déplacer.\n\n"
        "Ce message ne confirme pas la disponibilité actuelle du produit."
    )

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as smtp:
            if settings.SMTP_USE_STARTTLS:
                smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("Unable to deliver patient availability alert") from error
