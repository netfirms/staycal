import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "GoStayPro"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "staycal_session")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./staycal.db")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    # Cloudinary connection string, e.g., cloudinary://<api_key>:<api_secret>@<cloud_name>
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    # Default admin bootstrap (used on startup if no admin exists)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@staycal.local")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin12345")
    # Subscription pricing (THB)
    PLAN_BASIC_MONTHLY: float = float(os.getenv("PLAN_BASIC_MONTHLY", "249"))
    PLAN_BASIC_YEARLY: float = float(os.getenv("PLAN_BASIC_YEARLY", "2490"))
    PLAN_PRO_MONTHLY: float = float(os.getenv("PLAN_PRO_MONTHLY", "699"))
    PLAN_PRO_YEARLY: float = float(os.getenv("PLAN_PRO_YEARLY", "6990"))
    # Upload constraints
    UPLOAD_IMAGE_MAX_MB: int = int(os.getenv("UPLOAD_IMAGE_MAX_MB", "5"))
    UPLOAD_IMAGE_MAX_BYTES: int = UPLOAD_IMAGE_MAX_MB * 1024 * 1024
    # reCAPTCHA (optional)
    RECAPTCHA_SITE_KEY: str = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY: str = os.getenv("RECAPTCHA_SECRET_KEY", "")
    # reCAPTCHA version: "v2" (checkbox) or "v3" (score-based)
    RECAPTCHA_VERSION: str = os.getenv("RECAPTCHA_VERSION", "v3").lower()
    # For v3 only
    RECAPTCHA_MIN_SCORE: float = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.5"))
    RECAPTCHA_EXPECTED_ACTION: str = os.getenv("RECAPTCHA_EXPECTED_ACTION", "login")
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    RATE_LIMIT_AUTH: str = os.getenv("RATE_LIMIT_AUTH", "5/minute")
    RATE_LIMIT_AUTH_API: str = os.getenv("RATE_LIMIT_AUTH_API", "10/minute")

settings = Settings()
