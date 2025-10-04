from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def ensure_mvp_schema():
    """
    Lightweight, best-effort schema adjustments for MVP environments without Alembic.
    Ensures columns added post-initialization exist in existing databases.
    Currently ensures bookings.comment exists.
    """
    url = settings.DATABASE_URL
    try:
        with engine.connect() as conn:
            if url.startswith("sqlite"):
                # Check existing columns via PRAGMA
                res = conn.exec_driver_sql("PRAGMA table_info(bookings);")
                col_names = [row[1] for row in res]
                if "comment" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE bookings ADD COLUMN comment TEXT;")
            else:
                # Attempt Postgres-compatible add-if-missing
                try:
                    conn.exec_driver_sql("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS comment TEXT;")
                except Exception:
                    # Fallback: ignore if not supported / already present
                    pass
    except Exception:
        # Never fail app startup due to best-effort migration
        pass
