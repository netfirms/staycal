import logging
import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi.templating import Jinja2Templates
from ..config import settings

logger = logging.getLogger(__name__)

# Conditionally configure mail settings
mail_conf = {
    "MAIL_USERNAME": settings.MAIL_USERNAME,
    "MAIL_PASSWORD": settings.MAIL_PASSWORD,
    "MAIL_FROM": settings.MAIL_FROM,
    "MAIL_PORT": settings.MAIL_PORT,
    "MAIL_SERVER": settings.MAIL_SERVER,
    "USE_CREDENTIALS": True,
    "VALIDATE_CERTS": True
}

if settings.MAIL_SSL_TLS:
    mail_conf["MAIL_SSL_TLS"] = True
    mail_conf["MAIL_STARTTLS"] = False
else:
    mail_conf["MAIL_SSL_TLS"] = False
    mail_conf["MAIL_STARTTLS"] = True

# Create a reusable FastMail instance
fm = FastMail(ConnectionConfig(**mail_conf))

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

async def send_verification_email(email: str, token: str):
    """Sends a verification email to a new user using a Jinja2 template."""

    verification_url = f"{settings.BASE_URL}/auth/verify?token={token}"
    
    template_body = templates.get_template("emails/verification.html").render({
        "verification_url": verification_url,
        "current_year": datetime.datetime.now().year
    })

    message = MessageSchema(
        subject="Verify Your Email Address for GoStayPro",
        recipients=[email],
        body=template_body,
        subtype="html"
    )

    try:
        await fm.send_message(message)
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
