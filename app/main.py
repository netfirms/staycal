from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import Base, engine
from . import models  # ensure models are imported so tables are registered
from .routers import auth_views, app_views, calendar_htmx_views, admin_views, public_views

# Create tables for MVP (use Alembic in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="StayCal")

app.include_router(public_views.router)
app.include_router(auth_views.router)
app.include_router(app_views.router)
app.include_router(calendar_htmx_views.router)
app.include_router(admin_views.router)

# Static (placeholder)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
