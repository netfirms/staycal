import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .db import SessionLocal
from .limiter import limiter
from .models import User
from .routers import auth_views, app_views, calendar_htmx_views, admin_views, public_views
from .routers import rooms_views, bookings_views, homestays_views
from .routers import settings_views, ui_components
from .security import hash_password
from .templating import templates

# --- Logging configuration ---
_level = logging.DEBUG if getattr(settings, "DEBUG", False) else logging.INFO
logging.basicConfig(
    level=_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
# Align uvicorn loggers with our level (useful under Docker Compose)
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_name).setLevel(_level)
logger = logging.getLogger("app.startup")
logger.info("Starting %s (DEBUG=%s)", settings.APP_NAME, getattr(settings, "DEBUG", False))

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        f"{settings.APP_NAME}: Calendar-first homestay management.\n\n"
        "Swagger UI includes both web and mobile endpoints. "
        "Use the 'mobile-api' tag to view the Mobile JSON API."
    ),
    openapi_tags=[
        {
            "name": "mobile-api",
            "description": (
                f"Mobile JSON API for the {settings.APP_NAME} mobile application. "
                "Session-cookie based auth. Endpoints under /api/v1."
            ),
        }
    ],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    max_age=settings.SESSION_MAX_AGE_DAYS * 24 * 60 * 60 # days in seconds
)

@app.on_event("startup")
def startup_event():
    """Runs startup tasks, like ensuring a default admin exists."""
    logger.info("Running startup tasks...")

    def _ensure_default_admin():
        db = SessionLocal()
        try:
            if db.query(User).filter(User.role == "admin").first():
                return
            email = getattr(settings, "ADMIN_EMAIL", "admin@staycal.local")
            password = getattr(settings, "ADMIN_PASSWORD", "admin12345")
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.role = "admin"
            else:
                user = User(email=email, hashed_password=hash_password(password), role="admin", is_verified=True)
                db.add(user)
            db.commit()
            logger.info("Default admin user ensured.")
        finally:
            db.close()

    _ensure_default_admin()
    logger.info("Startup tasks complete.")


# Add the limiter to the app state
app.state.limiter = limiter
# Add the exception handler for rate limit exceeded errors
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(public_views.router)
app.include_router(auth_views.router)
app.include_router(app_views.router)
app.include_router(calendar_htmx_views.router)
app.include_router(admin_views.router)
app.include_router(rooms_views.router)
app.include_router(bookings_views.router)
app.include_router(homestays_views.router)
app.include_router(settings_views.router)
app.include_router(ui_components.router)

# Mobile JSON API
from .routers import api_mobile
app.include_router(api_mobile.router)

# Static (placeholder)
app.mount("/static", StaticFiles(directory="app/static", check_dir=False), name="static")

@app.get("/healthz")
@limiter.exempt
def healthz():
    return {"status": "ok"}


# Convenience: Mobile API Swagger shortcut
@app.get("/api/v1/docs", include_in_schema=False)
@limiter.exempt
def mobile_docs_redirect():
    # Jump to the mobile-api tag section in Swagger UI
    return RedirectResponse(url="/docs#/mobile-api")
