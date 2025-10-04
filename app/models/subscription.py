from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, UniqueConstraint
from ..db import Base

class PlanName(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"

class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_subscription_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan_name: Mapped[PlanName] = mapped_column(Enum(PlanName), default=PlanName.FREE, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="subscriptions")
