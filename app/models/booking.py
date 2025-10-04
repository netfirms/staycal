from datetime import date
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, ForeignKey, Date, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

class BookingStatus(str, PyEnum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    guest_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guest_contact: Mapped[str] = mapped_column(String(200), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Numeric(10,2), nullable=True)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.TENTATIVE, nullable=False)

    room: Mapped["Room"] = relationship(back_populates="bookings")

    def overlaps(self, other_start: date, other_end: date) -> bool:
        return not (self.end_date <= other_start or self.start_date >= other_end)
