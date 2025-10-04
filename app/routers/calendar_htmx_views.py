import calendar as cal
from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Booking, Room, BookingStatus
from ..security import get_current_user_id
from ..services.auto_checkout import run_auto_checkout

router = APIRouter(prefix="/htmx", tags=["calendar"]) 
templates = Jinja2Templates(directory="app/templates")

@router.get("/calendar/view", response_class=HTMLResponse)
def calendar_view(request: Request, year: int, month: int, room_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    # Auto-checkout before rendering calendar so statuses are up to date
    try:
        run_auto_checkout(db)
    except Exception:
        pass
    first_wd, days = cal.monthrange(year, month)  # Monday=0 .. Sunday=6
    start = date(year, month, 1)
    end = date(year, month, days)
    bookings = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date <= end, Booking.end_date >= start).all()
    month_label = f"{cal.month_name[month]} {year}"
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_str = date.today().isoformat()
    return templates.TemplateResponse(
        "calendar/grid.html",
        {
            "request": request,
            "year": year,
            "month": month,
            "days": days,
            "bookings": bookings,
            "room_id": room_id,
            "first_wd": first_wd,
            "weekdays": weekdays,
            "month_label": month_label,
            "today_str": today_str,
        },
    )

@router.get("/booking/new", response_class=HTMLResponse)
def booking_new(request: Request, room_id: int, start_date: str, end_date: str, db: Session = Depends(get_db)):
    default_rate = None
    try:
        room = db.query(Room).get(room_id)
        if room and room.default_rate is not None:
            default_rate = float(room.default_rate)
    except Exception:
        default_rate = None
    return templates.TemplateResponse("calendar/booking_modal.html", {"request": request, "room_id": room_id, "start_date": start_date, "end_date": end_date, "default_rate": default_rate})

@router.post("/booking/save", response_class=HTMLResponse)
def booking_save(request: Request, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str = Form(""), start_date: str = Form(...), end_date: str = Form(...), price: float = Form(0.0), comment: str = Form("") ):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    # conflict detection
    conflicts = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        return HTMLResponse("<div class='text-red-600 p-2'>Conflict: dates overlap existing booking.</div>", status_code=400)
    booking = Booking(room_id=room_id, guest_name=guest_name, guest_contact=guest_contact, start_date=s, end_date=e, price=price, status=BookingStatus.CONFIRMED, comment=comment.strip() or None)
    db.add(booking)
    db.commit()
    # Inform HTMX/JS listeners so calendars can refresh
    headers = {"HX-Trigger": "bookingSaved"}
    return HTMLResponse("<div class='text-green-700 p-2'>Booking saved.</div>", headers=headers)

@router.get("/calendar/events")
def calendar_events(request: Request, room_id: int, start: str, end: str, db: Session = Depends(get_db)):
    """Return bookings for a room within a given range in FullCalendar JSON format."""
    uid = get_current_user_id(request)
    if not uid:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # Parse dates (FullCalendar passes ISO8601, we only need the date portion)
    try:
        start_date = date.fromisoformat(start[:10])
        end_date = date.fromisoformat(end[:10])
    except Exception:
        return JSONResponse([], status_code=200)
    # Overlap query
    bookings = (
        db.query(Booking)
        .filter(
            Booking.room_id == room_id,
            Booking.start_date < end_date,
            Booking.end_date > start_date,
        )
        .all()
    )
    # Map status to colors
    def color_for(status: BookingStatus) -> str:
        if status == BookingStatus.CONFIRMED:
            return "#86efac"  # green-300
        if status == BookingStatus.CHECKED_IN:
            return "#93c5fd"  # blue-300
        if status == BookingStatus.CHECKED_OUT:
            return "#d1d5db"  # gray-300
        if status == BookingStatus.CANCELLED:
            return "#fca5a5"  # red-300
        return "#fde68a"      # yellow-300 tentative
    events = [
        {
            "id": b.id,
            "title": b.guest_name,
            "start": b.start_date.isoformat(),
            "end": b.end_date.isoformat(),  # end is exclusive in FullCalendar
            "allDay": True,
            "color": color_for(b.status),
        }
        for b in bookings
    ]
    return JSONResponse(events)

@router.post("/booking/update-status", response_class=HTMLResponse)
def update_status(request: Request, db: Session = Depends(get_db), booking_id: int = Form(...), status: str = Form(...)):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<div>Not found</div>", status_code=404)
    if status not in [s.value for s in BookingStatus]:
        return HTMLResponse("<div>Bad status</div>", status_code=400)
    b.status = BookingStatus(status)
    db.commit()
    return HTMLResponse("<div class='text-blue-700 p-2'>Status updated.</div>")
