from sqlalchemy import Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    homestay_id: Mapped[int] = mapped_column(ForeignKey("homestays.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    default_rate: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    homestay: Mapped["Homestay"] = relationship(back_populates="rooms")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room", cascade="all, delete-orphan")
