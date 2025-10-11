import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "GoStayPro"
    # Core settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # Auth & Session
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "staycal_session")
    SESSION_MAX_AGE_DAYS: int = int(os.getenv("SESSION_MAX_AGE_DAYS", "30"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./staycal.db")
    
    # Cloudinary
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    
    # Default admin bootstrap
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@staycal.local")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin12345")
    ADMIN_NOTIFICATION_EMAIL: str = os.getenv("ADMIN_NOTIFICATION_EMAIL", "")
    ADMIN_NOTIFICATION_EMAIL_ENABLE: bool = os.getenv("ADMIN_NOTIFICATION_EMAIL_ENABLE", "false").lower() == "true"
    
    # Mail Settings (Mailgun)
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@gostay.pro")
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY", "")
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN", "")

    # Firebase (for client-side analytics)
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    FIREBASE_MESSAGING_SENDER_ID: str = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "")
    FIREBASE_APP_ID: str = os.getenv("FIREBASE_APP_ID", "")
    FIREBASE_MEASUREMENT_ID: str = os.getenv("FIREBASE_MEASUREMENT_ID", "")

    # Upload constraints
    UPLOAD_IMAGE_MAX_MB: int = int(os.getenv("UPLOAD_IMAGE_MAX_MB", "5"))
    UPLOAD_IMAGE_MAX_BYTES: int = UPLOAD_IMAGE_MAX_MB * 1024 * 1024
    
    # reCAPTCHA (optional)
    RECAPTCHA_SITE_KEY: str = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY: str = os.getenv("RECAPTCHA_SECRET_KEY", "")
    RECAPTCHA_VERSION: str = os.getenv("RECAPTCHA_VERSION", "v3").lower()
    RECAPTCHA_MIN_SCORE: float = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.5"))
    RECAPTCHA_EXPECTED_ACTION: str = os.getenv("RECAPTCHA_EXPECTED_ACTION", "login")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    RATE_LIMIT_AUTH: str = os.getenv("RATE_LIMIT_AUTH", "5/minute")
    RATE_LIMIT_AUTH_API: str = os.getenv("RATE_LIMIT_AUTH_API", "10/minute")

settings = Settings()
