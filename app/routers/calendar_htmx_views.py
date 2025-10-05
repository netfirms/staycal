import calendar as cal
from datetime import date
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Booking, Room, BookingStatus, User
from ..security import get_current_user_id
from ..services.auto_checkout import run_auto_checkout
from ..services.media import save_image

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

@router.get("/booking/edit-dates", response_class=HTMLResponse)
def booking_edit_dates(request: Request, booking_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<div>Not found</div>", status_code=404)
    return templates.TemplateResponse(
        "calendar/edit_dates_modal.html",
        {
            "request": request,
            "booking": b,
        },
    )

@router.post("/booking/update-dates", response_class=HTMLResponse)
def booking_update_dates(
    request: Request,
    db: Session = Depends(get_db),
    booking_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<div>Not found</div>", status_code=404)
    try:
        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)
    except Exception:
        return HTMLResponse("<div class='text-red-700 p-2'>Invalid dates.</div>", status_code=400)
    # normalize ensure start < end
    if not (s < e):
        return HTMLResponse("<div class='text-red-700 p-2'>End date must be after start date.</div>", status_code=400)
    # conflict detection excluding self
    conflicts = (
        db.query(Booking)
        .filter(
            Booking.room_id == b.room_id,
            Booking.id != b.id,
            Booking.start_date < e,
            Booking.end_date > s,
        )
        .all()
    )
    if conflicts:
        return HTMLResponse("<div class='text-red-700 p-2'>Conflict: overlapping booking exists.</div>", status_code=400)
    b.start_date = s
    b.end_date = e
    db.commit()
    headers = {"HX-Trigger": "bookingUpdated"}
    # Return empty modal container to close
    return HTMLResponse("", headers=headers)


@router.get("/booking/edit", response_class=HTMLResponse)
def booking_edit(request: Request, booking_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<div>Not found</div>", status_code=404)
    user = db.query(User).get(uid)
    rooms = []
    if user and user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return templates.TemplateResponse(
        "calendar/edit_booking_modal.html",
        {
            "request": request,
            "booking": b,
            "rooms": rooms,
            "BookingStatus": BookingStatus,
        },
    )


@router.post("/booking/update", response_class=HTMLResponse)
async def booking_update(
    request: Request,
    db: Session = Depends(get_db),
    booking_id: int = Form(...),
    room_id: int = Form(...),
    guest_name: str = Form(...),
    guest_contact: str = Form(""),
    start_date: str = Form(...),
    end_date: str = Form(...),
    price: float | None = Form(None),
    status: str = Form(BookingStatus.CONFIRMED.value),
    comment: str = Form(""),
    image: UploadFile | None = File(None),
):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<div>Not found</div>", status_code=404)
    user = db.query(User).get(uid)
    # Validate room belongs to user's active homestay
    room = db.query(Room).get(room_id)
    if not room or (user and user.homestay_id and room.homestay_id != user.homestay_id):
        return HTMLResponse("<div class='text-red-700 p-2'>Invalid room selection.</div>", status_code=400)
    # Parse and validate dates
    try:
        s = date.fromisoformat(start_date)
        e = date.fromisoformat(end_date)
    except Exception:
        return HTMLResponse("<div class='text-red-700 p-2'>Invalid dates.</div>", status_code=400)
    if not (s < e):
        return HTMLResponse("<div class='text-red-700 p-2'>End date must be after start date.</div>", status_code=400)
    # Conflict detection excluding this booking
    conflicts = (
        db.query(Booking)
        .filter(
            Booking.room_id == room_id,
            Booking.id != booking_id,
            Booking.start_date < e,
            Booking.end_date > s,
        )
        .all()
    )
    if conflicts:
        return HTMLResponse("<div class='text-red-700 p-2'>Conflict: overlapping booking exists.</div>", status_code=400)
    # Apply changes
    b.room_id = room_id
    b.guest_name = guest_name.strip()
    b.guest_contact = guest_contact.strip()
    b.start_date = s
    b.end_date = e
    b.price = price
    try:
        b.status = BookingStatus(status)
    except Exception:
        return HTMLResponse("<div class='text-red-700 p-2'>Invalid status.</div>", status_code=400)
    b.comment = (comment.strip() or None)
    if image and image.filename:
        data = await image.read()
        new_url = save_image(data, image.filename, folder="staycal/bookings")
        if new_url:
            b.image_url = new_url
    db.commit()
    headers = {"HX-Trigger": "bookingUpdated"}
    return HTMLResponse("", headers=headers)
