from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

class UserRole(str):
    ADMIN = "admin"
    OWNER = "owner"
    STAFF = "staff"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.OWNER, nullable=False)
    homestay_id: Mapped[int | None] = mapped_column(ForeignKey("homestays.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    homestay: Mapped["Homestay" | None] = relationship(back_populates="users")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
