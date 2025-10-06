from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import Base, engine, ensure_mvp_schema, SessionLocal
from . import models  # ensure models are imported so tables are registered
from .routers import auth_views, app_views, calendar_htmx_views, admin_views, public_views
from .routers import rooms_views, bookings_views, homestays_views
from .config import settings
from .models import User
from .security import hash_password

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

app = FastAPI(title="StayCal")

app.include_router(public_views.router)
app.include_router(auth_views.router)
app.include_router(app_views.router)
app.include_router(calendar_htmx_views.router)
app.include_router(admin_views.router)
app.include_router(rooms_views.router)
app.include_router(bookings_views.router)
app.include_router(homestays_views.router)

# Static (placeholder)
app.mount("/static", StaticFiles(directory="app/static", check_dir=False), name="static")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
