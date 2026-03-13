import os
from datetime import timedelta

db_url = os.environ.get("DB_URL", "sqlite://:memory:")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Basic auth/JWT settings following FastAPI security guide
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# SMTP settings for contact form (Gmail: use App Password, not account password)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@brighter.bg")

# Cloudflare Turnstile
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")

# Contact form rate limit (requests per IP per window)
CONTACT_RATE_LIMIT = int(os.environ.get("CONTACT_RATE_LIMIT", "5"))
CONTACT_RATE_WINDOW = int(os.environ.get("CONTACT_RATE_WINDOW", "3600"))  # seconds


NOTIFICATIONS_MS_URL = os.environ.get(
    "NOTIFICATIONS_MS_URL", "http://notifications-ms:8004"
)
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")


def access_token_expires_delta() -> timedelta:
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
