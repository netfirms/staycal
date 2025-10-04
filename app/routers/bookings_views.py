from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Room, Booking, BookingStatus
from ..security import get_current_user_id
from ..services.auto_checkout import run_auto_checkout

router = APIRouter(prefix="/app/bookings", tags=["bookings"])
templates = Jinja2Templates(directory="app/templates")


def require_user(request: Request, db: Session) -> User | None:
    uid = get_current_user_id(request)
    if not uid:
        return None
    return db.query(User).get(uid)


@router.get("/", response_class=HTMLResponse)
def bookings_index(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    # Auto-checkout past stays before listing
    try:
        run_auto_checkout(db)
    except Exception:
        pass
    # Fetch bookings for rooms belonging to this user's homestay
    bookings = []
    rooms_map = {}
    if user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).all()
        room_ids = [r.id for r in rooms]
        rooms_map = {r.id: r for r in rooms}
        if room_ids:
            bookings = db.query(Booking).filter(Booking.room_id.in_(room_ids)).order_by(Booking.start_date.desc()).all()
    return templates.TemplateResponse("bookings/index.html", {"request": request, "user": user, "bookings": bookings, "rooms_map": rooms_map, "BookingStatus": BookingStatus})


@router.get("/new", response_class=HTMLResponse)
def bookings_new(request: Request, db: Session = Depends(get_db), room_id: int | None = None):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    rooms = []
    if user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return templates.TemplateResponse("bookings/form.html", {"request": request, "user": user, "rooms": rooms, "mode": "new", "selected_room_id": room_id, "BookingStatus": BookingStatus})


@router.post("/new")
def bookings_create(request: Request, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str = Form(""), start_date: str = Form(...), end_date: str = Form(...), price: float | None = Form(None), status: str = Form(BookingStatus.CONFIRMED.value), comment: str = Form("") ):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Room not found</h2>", status_code=404)
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    conflicts = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        return HTMLResponse("<div class='p-3 text-red-700'>Conflict: overlapping booking exists.</div>", status_code=400)
    b = Booking(room_id=room_id, guest_name=guest_name.strip(), guest_contact=guest_contact.strip(), start_date=s, end_date=e, price=price, status=BookingStatus(status), comment=comment.strip() or None)
    db.add(b)
    db.commit()
    return RedirectResponse(url="/app/bookings/", status_code=303)


@router.get("/{booking_id}/edit", response_class=HTMLResponse)
def bookings_edit_form(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    room = db.query(Room).get(b.room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return templates.TemplateResponse("bookings/form.html", {"request": request, "user": user, "rooms": rooms, "mode": "edit", "booking": b, "BookingStatus": BookingStatus})


@router.post("/{booking_id}/edit")
def bookings_edit(request: Request, booking_id: int, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str = Form(""), start_date: str = Form(...), end_date: str = Form(...), price: float | None = Form(None), status: str = Form(BookingStatus.CONFIRMED.value), comment: str = Form("") ):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    conflicts = db.query(Booking).filter(Booking.room_id == room_id, Booking.id != booking_id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        return HTMLResponse("<div class='p-3 text-red-700'>Conflict: overlapping booking exists.</div>", status_code=400)
    b.room_id = room_id
    b.guest_name = guest_name.strip()
    b.guest_contact = guest_contact.strip()
    b.start_date = s
    b.end_date = e
    b.price = price
    b.status = BookingStatus(status)
    b.comment = (comment.strip() or None)
    db.commit()
    return RedirectResponse(url="/app/bookings/", status_code=303)


@router.post("/{booking_id}/delete")
def bookings_delete(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    b = db.query(Booking).get(booking_id)
    if not b:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    room = db.query(Room).get(b.room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    db.delete(b)
    db.commit()
    return RedirectResponse(url="/app/bookings/", status_code=303)
