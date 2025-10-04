from datetime import date
from sqlalchemy.orm import Session
from ..models import Booking, BookingStatus


def run_auto_checkout(db: Session) -> int:
    """
    Automatically mark bookings as checked out if their end_date is in the past.
    We consider bookings with status tentative, confirmed, or checked_in as eligible.
    Returns the number of rows affected (best-effort; may be 0 if unsupported by backend).
    """
    today = date.today()
    # Bulk update eligible bookings
    q = (
        db.query(Booking)
        .filter(
            Booking.end_date < today,
            Booking.status.in_(
                [
                    BookingStatus.TENTATIVE,
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECKED_IN,
                ]
            ),
        )
    )
    # Use bulk update for efficiency; synchronize_session=False for speed.
    result = q.update({Booking.status: BookingStatus.CHECKED_OUT}, synchronize_session=False)
    db.commit()
    try:
        return int(result)
    except Exception:
        return 0
