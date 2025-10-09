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
    - Ensure new columns exist (added over time)
    - Ensure helpful indexes exist for common queries
    - Ensure unique owner per subscription is enforced (via unique index if needed)
    Never fails app startup; best-effort only.
    """
    url = settings.DATABASE_URL
    try:
        with engine.connect() as conn:
            if url.startswith("sqlite"):
                # bookings table - add missing columns
                res = conn.exec_driver_sql("PRAGMA table_info(bookings);")
                col_names = [row[1] for row in res]
                if "comment" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE bookings ADD COLUMN comment TEXT;")
                if "image_url" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE bookings ADD COLUMN image_url VARCHAR(500);")
                # homestays table - add missing columns
                res = conn.exec_driver_sql("PRAGMA table_info(homestays);")
                col_names = [row[1] for row in res]
                if "image_url" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE homestays ADD COLUMN image_url VARCHAR(500);")
                # rooms table - add missing columns
                res = conn.exec_driver_sql("PRAGMA table_info(rooms);")
                col_names = [row[1] for row in res]
                if "image_url" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE rooms ADD COLUMN image_url VARCHAR(500);")
                if "ota_ical_url" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE rooms ADD COLUMN ota_ical_url VARCHAR(500);")
                # users table - add missing columns if needed (older DBs)
                res = conn.exec_driver_sql("PRAGMA table_info(users);")
                col_names = [row[1] for row in res]
                if "homestay_id" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN homestay_id INTEGER;")
                if "currency" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN currency VARCHAR(8) DEFAULT 'USD' NOT NULL;")
                # indexes for faster lookups (IF NOT EXISTS is supported by SQLite)
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_bookings_room_id ON bookings(room_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_bookings_start_date ON bookings(start_date);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_bookings_end_date ON bookings(end_date);"
                )
                # composite index helps overlap searches
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_bookings_room_start_end ON bookings(room_id, start_date, end_date);"
                )
                # unique owner per subscription (SQLite: unique index works like constraint)
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_owner ON subscriptions(owner_id);"
                )
            else:
                # Postgres-compatible add-if-missing
                for ddl in [
                    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS comment TEXT;",
                    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
                    "ALTER TABLE homestays ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS ota_ical_url VARCHAR(500);",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS homestay_id INTEGER;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS currency VARCHAR(8) DEFAULT 'USD' NOT NULL;",
                    "ALTER TABLE users ALTER COLUMN currency SET DEFAULT 'USD';",
                ]:
                    try:
                        conn.exec_driver_sql(ddl)
                    except Exception:
                        pass
                # indexes (IF NOT EXISTS is supported in PG 9.5+)
                for idx in [
                    "CREATE INDEX IF NOT EXISTS ix_bookings_room_id ON bookings(room_id);",
                    "CREATE INDEX IF NOT EXISTS ix_bookings_start_date ON bookings(start_date);",
                    "CREATE INDEX IF NOT EXISTS ix_bookings_end_date ON bookings(end_date);",
                    "CREATE INDEX IF NOT EXISTS ix_bookings_room_start_end ON bookings(room_id, start_date, end_date);",
                ]:
                    try:
                        conn.exec_driver_sql(idx)
                    except Exception:
                        pass
                # ensure unique one subscription per owner (if schema was created without constraint)
                try:
                    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_owner ON subscriptions(owner_id);")
                except Exception:
                    pass
    except Exception:
        # Never fail app startup due to best-effort migration
        pass
