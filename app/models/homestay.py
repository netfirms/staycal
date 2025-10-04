from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

class Homestay(Base):
    __tablename__ = "homestays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="homestay", foreign_keys=[owner_id])
    rooms: Mapped[list["Room"]] = relationship(back_populates="homestay", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(back_populates="homestay")
