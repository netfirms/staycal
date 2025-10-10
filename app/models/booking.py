from __future__ import annotations
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, ForeignKey, Date, Numeric, Text, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

if TYPE_CHECKING:
    from .room import Room

class BookingStatus(str, PyEnum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    guest_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guest_contact: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.TENTATIVE, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    room: Mapped[Room] = relationship(back_populates="bookings")
