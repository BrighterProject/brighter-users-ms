from email.message import EmailMessage

import aiosmtplib
import httpx
from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, EmailStr

from app.cache import check_contact_rate_limit
from app.limiter import limiter
from app.settings import (
    CONTACT_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TURNSTILE_SECRET_KEY,
)

router = APIRouter(prefix="/auth", tags=["contact"])

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    turnstile_token: str


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _verify_turnstile(token: str, ip: str) -> bool:
    if not TURNSTILE_SECRET_KEY:
        logger.warning("TURNSTILE_SECRET_KEY not set — skipping captcha verification")
        return True

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            TURNSTILE_VERIFY_URL,
            data={"secret": TURNSTILE_SECRET_KEY, "response": token, "remoteip": ip},
        )
        result = resp.json()

    if not result.get("success"):
        logger.warning("Turnstile verification failed: {}", result)
        return False
    return True


@router.post("/contact", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def send_contact_message(request: Request, body: ContactRequest):
    client_ip = _get_client_ip(request)

    # Rate limit
    if not await check_contact_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # Turnstile CAPTCHA
    try:
        if not await _verify_turnstile(body.turnstile_token, client_ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPTCHA verification failed",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Turnstile verification error: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CAPTCHA verification unavailable",
        )

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured — cannot send contact email")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured",
        )

    msg = EmailMessage()
    msg["Subject"] = f"[Brighter.BG Contact] {body.subject}"
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
