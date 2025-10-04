from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Booking, Room, BookingStatus
from ..security import get_current_user_id

router = APIRouter(prefix="/htmx", tags=["calendar"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/calendar/view", response_class=HTMLResponse)
def calendar_view(request: Request, year: int, month: int, room_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    _, days = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, days)
    bookings = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date <= end, Booking.end_date >= start).all()
    return templates.TemplateResponse("calendar/grid.html", {"request": request, "year": year, "month": month, "days": days, "bookings": bookings, "room_id": room_id})

@router.get("/booking/new", response_class=HTMLResponse)
def booking_new(request: Request, room_id: int, start_date: str, end_date: str):
    return templates.TemplateResponse("calendar/booking_modal.html", {"request": request, "room_id": room_id, "start_date": start_date, "end_date": end_date})

@router.post("/booking/save", response_class=HTMLResponse)
def booking_save(request: Request, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str = Form(""), start_date: str = Form(...), end_date: str = Form(...), price: float = Form(0.0),):
    uid = get_current_user_id(request)
    if not uid:
        return HTMLResponse("<div>Please login</div>", status_code=401)
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    # conflict detection
    conflicts = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        return HTMLResponse("<div class='text-red-600 p-2'>Conflict: dates overlap existing booking.</div>", status_code=400)
    booking = Booking(room_id=room_id, guest_name=guest_name, guest_contact=guest_contact, start_date=s, end_date=e, price=price, status=BookingStatus.CONFIRMED)
    db.add(booking)
    db.commit()
    return HTMLResponse("<div class='text-green-700 p-2'>Booking saved.</div>")

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
