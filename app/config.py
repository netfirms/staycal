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

settings = Settings()
