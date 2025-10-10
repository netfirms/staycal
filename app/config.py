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
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./staycal.db")
    
    # Cloudinary
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    
    # Default admin bootstrap
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@staycal.local")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin12345")
    
    # Mail Settings
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.mailtrap.io")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "2525"))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@gostay.pro")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"

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
