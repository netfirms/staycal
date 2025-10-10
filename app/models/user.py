from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base
from enum import Enum

class UserRole(str, Enum):
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
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)

    # Email verification fields
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)

    # User is staff/member of a homestay via users.homestay_id -> homestays.id
    homestay: Mapped[Optional["Homestay"]] = relationship(back_populates="users", foreign_keys=[homestay_id])

    # Owner relationship: a user may own one or more homestays via homestays.owner_id -> users.id
    homestays_owned: Mapped[list["Homestay"]] = relationship(back_populates="owner", foreign_keys="Homestay.owner_id")

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
