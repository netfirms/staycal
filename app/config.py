import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "StayCal"
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

settings = Settings()
