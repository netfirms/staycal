from sqlalchemy import Integer, String, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    room_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship to subscriptions
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")
