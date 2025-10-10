import logging
import datetime
import requests
from fastapi.templating import Jinja2Templates
from ..config import settings

logger = logging.getLogger(__name__)

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

def send_verification_email(email: str, token: str):
    """Sends a verification email to a new user using the Mailgun API."""
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        logger.warning("Mailgun API key or domain not configured. Skipping email.")
        return

    verification_url = f"{settings.BASE_URL}/auth/verify?token={token}"
    
    template_body = templates.get_template("emails/verification.html").render({
        "verification_url": verification_url,
        "current_year": datetime.datetime.now().year
    })

    mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    auth = ("api", settings.MAILGUN_API_KEY)
    data = {
        "from": f"GoStayPro <{settings.MAIL_FROM}>",
        "to": [email],
        "subject": "Verify Your Email Address for GoStayPro",
        "html": template_body,
    }

    try:
        response = requests.post(mailgun_url, auth=auth, data=data, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        logger.info(f"Verification email sent to {email} via Mailgun.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send verification email to {email} via Mailgun: {e}")

def send_invitation_email(email: str, token: str):
    """Sends an invitation email to a new staff member using the Mailgun API."""
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        logger.warning("Mailgun API key or domain not configured. Skipping email.")
        return

    invitation_url = f"{settings.BASE_URL}/auth/accept-invitation?token={token}"
    
    template_body = templates.get_template("emails/invitation.html").render({
        "invitation_url": invitation_url,
        "current_year": datetime.datetime.now().year
    })

    mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    auth = ("api", settings.MAILGUN_API_KEY)
    data = {
        "from": f"GoStayPro <{settings.MAIL_FROM}>",
        "to": [email],
        "subject": "You're invited to join a property on GoStayPro",
        "html": template_body,
    }

    try:
        response = requests.post(mailgun_url, auth=auth, data=data, timeout=10)
        response.raise_for_status()
        logger.info(f"Invitation email sent to {email} via Mailgun.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send invitation email to {email} via Mailgun: {e}")

def send_password_reset_email(email: str, token: str):
    """Sends a password reset email to a user using the Mailgun API."""
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        logger.warning("Mailgun API key or domain not configured. Skipping email.")
        return

    reset_url = f"{settings.BASE_URL}/auth/reset-password?token={token}"
    
    template_body = templates.get_template("emails/password_reset.html").render({
        "reset_url": reset_url,
        "current_year": datetime.datetime.now().year
    })

    mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    auth = ("api", settings.MAILGUN_API_KEY)
    data = {
        "from": f"GoStayPro <{settings.MAIL_FROM}>",
        "to": [email],
        "subject": "Reset Your GoStayPro Password",
        "html": template_body,
    }

    try:
        response = requests.post(mailgun_url, auth=auth, data=data, timeout=10)
        response.raise_for_status()
        logger.info(f"Password reset email sent to {email} via Mailgun.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send password reset email to {email} via Mailgun: {e}")
