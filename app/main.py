from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import Base, engine, ensure_mvp_schema
from . import models  # ensure models are imported so tables are registered
from .routers import auth_views, app_views, calendar_htmx_views, admin_views, public_views
from .routers import rooms_views, bookings_views, homestays_views

# Create tables for MVP (use Alembic in production)
Base.metadata.create_all(bind=engine)
# Best-effort lightweight migrations (e.g., add missing columns for existing DBs)
ensure_mvp_schema()

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
