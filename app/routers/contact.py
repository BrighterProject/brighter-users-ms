from email.message import EmailMessage

import aiosmtplib
from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, EmailStr

from app.settings import CONTACT_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

router = APIRouter(prefix="/auth", tags=["contact"])


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


@router.post("/contact", status_code=status.HTTP_204_NO_CONTENT)
async def send_contact_message(body: ContactRequest):
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured — cannot send contact email")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured",
        )

    msg = EmailMessage()
    msg["Subject"] = f"[Ploshtadka.BG Contact] {body.subject}"
    msg["From"] = SMTP_USER
    msg["To"] = CONTACT_EMAIL
    msg["Reply-To"] = body.email
    msg.set_content(
        f"Name: {body.name}\n"
        f"Email: {body.email}\n"
        f"Subject: {body.subject}\n\n"
        f"{body.message}"
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Contact email sent from={} subject={}", body.email, body.subject)
    except Exception as exc:
        logger.error("Failed to send contact email: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send email",
        )
