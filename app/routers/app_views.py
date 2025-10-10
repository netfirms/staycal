from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import get_db
from ..models import User, Homestay, Room, Booking, BookingStatus
from ..security import get_current_user_id
from ..services.auto_checkout import run_auto_checkout
from ..templating import templates
from ..services import reporting

router = APIRouter(tags=["app"])

@router.get("/app", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    # Auto-checkout any past stays before presenting data
    try:
        run_auto_checkout(db)
    except Exception:
        pass
    rooms = []
    rooms_map = {}
    checkins_today = []
    checkouts_today = []
    upcoming_count = 0
    rooms_count = 0
    today = date.today()
    active = None
    analytics = {
        "monthly_bookings": 0, 
        "monthly_revenue": 0.0, 
        "month_start": date(today.year, today.month, 1),
        "occupancy_rate": 0.0,
        "adr": 0.0,
        "revpar": 0.0,
    }

    if user and user.homestay_id:
        active = db.query(Homestay).get(user.homestay_id)
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).all()
        rooms_count = len(rooms)
        rooms_map = {r.id: r for r in rooms}
        room_ids = [r.id for r in rooms]
        if room_ids:
            month_start = date(today.year, today.month, 1)
            days_in_month = (date(today.year, today.month + 1, 1) - month_start).days if today.month < 12 else 31
            
            # Monthly revenue and bookings
            analytics["monthly_bookings"] = db.query(func.count(Booking.id)).filter(Booking.room_id.in_(room_ids), Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month))).scalar() or 0
            monthly_revenue = db.query(func.coalesce(func.sum(Booking.price), 0)).filter(Booking.room_id.in_(room_ids), Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month)), Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value, BookingStatus.CHECKED_OUT.value])).scalar() or 0
            analytics["monthly_revenue"] = float(monthly_revenue)

            # Occupancy, ADR, RevPAR
            total_room_nights_in_month = rooms_count * days_in_month
            booked_nights_in_month = db.query(func.sum(Booking.end_date - Booking.start_date)).filter(Booking.room_id.in_(room_ids), Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month)), Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value])).scalar() or 0

            analytics["occupancy_rate"] = (booked_nights_in_month / total_room_nights_in_month) * 100 if total_room_nights_in_month > 0 else 0
            analytics["adr"] = analytics["monthly_revenue"] / booked_nights_in_month if booked_nights_in_month > 0 else 0
            analytics["revpar"] = analytics["monthly_revenue"] / total_room_nights_in_month if total_room_nights_in_month > 0 else 0

            checkins_today = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(room_ids),
                    Booking.start_date == today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .all()
            )
            checkouts_today = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(room_ids),
                    Booking.end_date == today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .all()
            )
            upcoming_count = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(room_ids),
                    Booking.start_date >= today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .count()
            )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "active": active,
            "rooms": rooms,
            "rooms_count": rooms_count,
            "rooms_map": rooms_map,
            "today": today,
            "checkins_today": checkins_today,
            "checkouts_today": checkouts_today,
            "upcoming_count": upcoming_count,
            "analytics": analytics,
        },
    )

@router.get("/app/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db), start: str | None = None, end: str | None = None):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Auto-checkout in case any past stays need status update
    try:
        run_auto_checkout(db)
    except Exception:
        pass

    # Parse optional period
    period_start = None
    period_end = None
    try:
        if start:
            period_start = date.fromisoformat(start)
        if end:
            period_end = date.fromisoformat(end)
    except ValueError:
        # Ignore bad inputs, treat as no period
        period_start, period_end = None, None
    # Default to current month if no bounds provided
    if period_start is None and period_end is None:
        today_ = date.today()
        first_of_month = date(today_.year, today_.month, 1)
        if today_.month == 12:
            first_of_next = date(today_.year + 1, 1, 1)
        else:
            first_of_next = date(today_.year, today_.month + 1, 1)
        period_start, period_end = first_of_month, first_of_next
    # Normalize if only one bound provided: if only start -> open-ended; if only end -> open-started

    # Collect homestays relevant to user
    owned = db.query(Homestay).filter(Homestay.owner_id == user.id).all()
    active = db.query(Homestay).get(user.homestay_id) if user.homestay_id else None

    # Build stats per homestay
    seen_ids = set()
    relevant = []
    for hs in owned:
        relevant.append(hs)
        seen_ids.add(hs.id)
    if active and active.id not in seen_ids:
        relevant.append(active)

    hs_blocks: list[dict] = []
    bookings_by_hs: dict[int, list[Booking]] = {}

    today = date.today()

    for hs in relevant:
        rooms = db.query(Room).filter(Room.homestay_id == hs.id).order_by(Room.name.asc()).all()
        room_ids = [r.id for r in rooms]
        bookings: list[Booking] = []
        checkins_today = 0
        checkouts_today = 0
        if room_ids:
            q = db.query(Booking).filter(Booking.room_id.in_(room_ids))
            # Apply period overlap filter if both bounds provided
            if period_start and period_end:
                q = q.filter(Booking.start_date < period_end, Booking.end_date > period_start)
            elif period_start:
                q = q.filter(Booking.end_date > period_start)
            elif period_end:
                q = q.filter(Booking.start_date < period_end)
            bookings = q.all()
            checkins_today = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(room_ids),
                    Booking.start_date == today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .count()
            )
            checkouts_today = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(room_ids),
                    Booking.end_date == today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .count()
            )
        bookings_by_hs[hs.id] = bookings

        # Compute stats
        nights = 0
        for b in bookings:
            if period_start or period_end:
                s = b.start_date
                e = b.end_date
                if period_start:
                    s = max(s, period_start)
                if period_end:
                    e = min(e, period_end)
                nights += max(0, (e - s).days)
            else:
                nights += max(0, (b.end_date - b.start_date).days)
        bookings_count = len(bookings)
        profit = float(sum(float(b.price or 0) for b in bookings))
        stats = {
            "nights": nights,
            "bookings": bookings_count,
            "profit": profit,
            "rooms_count": len(rooms),
            "checkins_today": checkins_today,
            "checkouts_today": checkouts_today,
        }
        hs_blocks.append({"homestay": hs, "rooms": rooms, "stats": stats})

    # Flatten combined list of bookings for quick view (recent first)
    all_bookings: list[Booking] = []
    for lst in bookings_by_hs.values():
        all_bookings.extend(lst)
    all_bookings.sort(key=lambda b: (b.start_date, b.id), reverse=True)

    # Upcoming check-ins for the active homestay (next ones by start_date)
    upcoming_checkins = []
    rooms_map = {}
    if active:
        active_rooms = db.query(Room).filter(Room.homestay_id == active.id).all()
        rooms_map = {r.id: r for r in active_rooms}
        active_room_ids = [r.id for r in active_rooms]
        if active_room_ids:
            upcoming_checkins = (
                db.query(Booking)
                .filter(
                    Booking.room_id.in_(active_room_ids),
                    Booking.start_date >= today,
                    Booking.status != BookingStatus.CANCELLED.value,
                )
                .order_by(Booking.start_date.asc(), Booking.id.asc())
                .limit(10)
                .all()
            )

    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "user": user,
            "owned": owned,
            "active": active,
            "hs_blocks": hs_blocks,
            "all_bookings": all_bookings,
            "period_start": period_start,
            "period_end": period_end,
            "upcoming_checkins": upcoming_checkins,
            "rooms_map": rooms_map,
        },
    )

# --- Report Downloads ---

def _get_overview_data(db: Session, user: User, start: str | None, end: str | None) -> tuple[list[Booking], dict, date, date]:
    # This helper function re-uses the data fetching logic from the overview page.
    period_start, period_end = None, None
    try:
        if start:
            period_start = date.fromisoformat(start)
        if end:
            period_end = date.fromisoformat(end)
    except ValueError:
        period_start, period_end = None, None

    if period_start is None and period_end is None:
        today_ = date.today()
        first_of_month = date(today_.year, today_.month, 1)
        if today_.month == 12:
            first_of_next = date(today_.year + 1, 1, 1)
        else:
            first_of_next = date(today_.year, today_.month + 1, 1)
        period_start, period_end = first_of_month, first_of_next

    # Fetch all bookings for the user within the period
    all_user_homestays = db.query(Homestay).filter(Homestay.owner_id == user.id).all()
    all_user_room_ids = [r.id for hs in all_user_homestays for r in hs.rooms]
    rooms_map = {r.id: r for hs in all_user_homestays for r in hs.rooms}

    q = db.query(Booking).filter(Booking.room_id.in_(all_user_room_ids))
    if period_start and period_end:
        q = q.filter(Booking.start_date < period_end, Booking.end_date > period_start)
    elif period_start:
        q = q.filter(Booking.end_date > period_start)
    elif period_end:
        q = q.filter(Booking.start_date < period_end)
    
    bookings = q.order_by(Booking.start_date.asc()).all()
    return bookings, rooms_map, period_start, period_end

@router.get("/app/analytics/download/csv")
def download_csv_report(request: Request, db: Session = Depends(get_db), start: str | None = None, end: str | None = None):
    uid = get_current_user_id(request)
    if not uid:
        return Response(status_code=401)
    user = db.query(User).get(uid)

    bookings, rooms_map, _, _ = _get_overview_data(db, user, start, end)
    csv_data = reporting.generate_csv_report(bookings, rooms_map)

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=booking_report_{date.today().isoformat()}.csv"}
    )

@router.get("/app/analytics/download/pdf")
def download_pdf_report(request: Request, db: Session = Depends(get_db), start: str | None = None, end: str | None = None):
    uid = get_current_user_id(request)
    if not uid:
        return Response(status_code=401)
    user = db.query(User).get(uid)

    bookings, rooms_map, period_start, period_end = _get_overview_data(db, user, start, end)
    pdf_bytes = reporting.generate_pdf_report(bookings, rooms_map, user, period_start, period_end)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=booking_report_{date.today().isoformat()}.pdf"}
    )
