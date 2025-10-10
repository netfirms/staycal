from datetime import date

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Room, Booking, BookingStatus
from ..security import get_current_user_id
from ..services.auto_checkout import run_auto_checkout
from ..services.ical import overlaps_ota, fetch_ota_events
from ..services.media import save_image

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
        db.rollback()
    # Fetch bookings for rooms belonging to this user's homestay
    bookings = []
    rooms_map = {}
    if user.homestay_id:
        print(user.homestay_id)
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).all()
        for r in rooms:
            print(r)
        room_ids = [r.id for r in rooms]
        rooms_map = {r.id: r for r in rooms}
        if room_ids:
            bookings = db.query(Booking).filter(Booking.room_id.in_(room_ids)).order_by(Booking.start_date.desc()).all()
            print(bookings)
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
async def bookings_create(request: Request, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str = Form(""), start_date: str = Form(...), end_date: str = Form(...), price: float | None = Form(None), status: str = Form(BookingStatus.CONFIRMED.value), comment: str = Form(""), image: UploadFile | None = File(None) ):
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
    # prevent overlaps with OTA calendar if configured
    if getattr(room, "ota_ical_url", None):
        try:
            ota_events = fetch_ota_events(room.ota_ical_url)
            if overlaps_ota(ota_events, s, e):
                return HTMLResponse("<div class='p-3 text-red-700'>Conflict: overlaps external OTA calendar.</div>", status_code=400)
        except Exception:
            pass
    img_url = None
    if image and image.filename:
        data = await image.read()
        img_url = save_image(data, image.filename, folder="staycal/bookings")
    print(status)
    print(BookingStatus(status))
    b = Booking(room_id=room_id, guest_name=guest_name.strip(), guest_contact=guest_contact.strip(), start_date=s, end_date=e, price=price, status=BookingStatus(status), comment=comment.strip() or None, image_url=img_url)
    db.add(b)
    db.commit()
    return RedirectResponse(url="/app/bookings/", status_code=303)


@router.get("/{booking_id}/edit", response_class=HTMLResponse)
def bookings_form_edit(request: Request, booking_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)

    booking = db.query(Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    rooms = db.query(Room).all()
    return templates.TemplateResponse(
        "bookings/form.html",
        {
            "request": request,
            "booking": booking,
            "rooms": rooms,
            "room_id": booking.room_id,
            "BookingStatus": BookingStatus,
        },
    )

@router.post("/create")
def bookings_create(request: Request, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str | None = Form(None), start_date: date = Form(...), end_date: date = Form(...), price: float | None = Form(None), status: str = Form(...), comment: str | None = Form(None)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)

    booking = Booking(
        room_id=room_id,
        guest_name=guest_name,
        guest_contact=guest_contact,
        start_date=start_date,
        end_date=end_date,
        price=price,
        status=BookingStatus(status),
        comment=comment,
    )
    db.add(booking)
    db.commit()
    return RedirectResponse(url="/app/bookings", status_code=303)

@router.post("/{booking_id}/edit")
def bookings_update(request: Request, booking_id: int, db: Session = Depends(get_db), room_id: int = Form(...), guest_name: str = Form(...), guest_contact: str | None = Form(None), start_date: date = Form(...), end_date: date = Form(...), price: float | None = Form(None), status: str = Form(...), comment: str | None = Form(None)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)

    booking = db.query(Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.room_id = room_id
    booking.guest_name = guest_name
    booking.guest_contact = guest_contact
    booking.start_date = start_date
    booking.end_date = end_date
    booking.price = price
    booking.status = BookingStatus(status).value
    booking.comment = comment

    db.commit()
    return RedirectResponse(url="/app/bookings", status_code=303)

@router.post("/{booking_id}/delete")
def bookings_delete(request: Request, booking_id: int, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)

    booking = db.query(Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()
    return RedirectResponse(url="/app/bookings", status_code=303)
