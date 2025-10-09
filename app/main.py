import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
from .db import Base, engine, ensure_mvp_schema, SessionLocal
from . import models  # ensure models are imported so tables are registered
from .routers import auth_views, app_views, calendar_htmx_views, admin_views, public_views
from .routers import rooms_views, bookings_views, homestays_views
from .routers import settings_views
from .config import settings
from .models import User
from .security import hash_password

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

# Create tables for MVP (use Alembic in production)
Base.metadata.create_all(bind=engine)
# Best-effort lightweight migrations (e.g., add missing columns for existing DBs)
ensure_mvp_schema()

# Bootstrap a default admin user if none exists
def _ensure_default_admin():
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.role == "admin").first()
        if exists:
            return
        email = getattr(settings, "ADMIN_EMAIL", "admin@staycal.local")
        password = getattr(settings, "ADMIN_PASSWORD", "admin12345")
        # If email is taken by a non-admin, promote it to admin
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = "admin"
        else:
            user = User(email=email, hashed_password=hash_password(password), role="admin")
            db.add(user)
        db.commit()
    except Exception:
        # Do not block startup if seeding fails
        db.rollback()
    finally:
        db.close()

_ensure_default_admin()

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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        # Use the limiter from the app state
        await app.state.limiter.check(request)
    except RateLimitExceeded as e:
        return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {e.detail}"})
    return await call_next(request)


app.include_router(public_views.router)
app.include_router(auth_views.router)
app.include_router(app_views.router)
app.include_router(calendar_htmx_views.router)
app.include_router(admin_views.router)
app.include_router(rooms_views.router)
app.include_router(bookings_views.router)
app.include_router(homestays_views.router)
app.include_router(settings_views.router)

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
