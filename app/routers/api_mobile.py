from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Homestay, Room, Booking, BookingStatus
from ..security import get_current_user_id, set_session, verify_password
from ..services.auto_checkout import run_auto_checkout
from ..services.ical import fetch_ota_events, overlaps_ota

router = APIRouter(prefix="/api/v1", tags=["mobile-api"]) 

# ==== Schemas ====
class UserOut(BaseModel):
    id: int
    email: str
    role: str
    homestay_id: int | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "owner@example.com",
                "role": "owner",
                "homestay_id": 10
            }
        }


class HomestayOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 10,
                "name": "Palm Breeze Homestay",
                "address": "123 Beach Rd, Phuket"
            }
        }


class RoomOut(BaseModel):
    id: int
    name: str
    capacity: Optional[int] = None
    default_rate: Optional[float] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 101,
                "name": "Deluxe Double Room",
                "capacity": 2,
                "default_rate": 1200.0
            }
        }


class BookingOut(BaseModel):
    id: int
    room_id: int
    guest_name: str
    guest_contact: Optional[str] = None
    start_date: date
    end_date: date
    price: Optional[float] = None
    status: BookingStatus
    comment: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        use_enum_values = True
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 555,
                "room_id": 101,
                "guest_name": "Jane Doe",
                "guest_contact": "+66-800-123-456",
                "start_date": "2025-10-07",
                "end_date": "2025-10-10",
                "price": 3500.0,
                "status": "confirmed",
                "comment": "Late arrival",
                "image_url": "https://res.cloudinary.com/demo/image/upload/v1690000000/staycal/bookings/abc.jpg"
            }
        }


class LoginIn(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "owner@example.com",
                "password": "admin12345"
            }
        }


class BookingCreateIn(BaseModel):
    room_id: int
    guest_name: str
    guest_contact: Optional[str] = ""
    start_date: date
    end_date: date
    price: Optional[float] = None
    status: BookingStatus = Field(default=BookingStatus.CONFIRMED)
    comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": 101,
                "guest_name": "Jane Doe",
                "guest_contact": "+66-800-123-456",
                "start_date": "2025-10-07",
                "end_date": "2025-10-10",
                "price": 3500.0,
                "status": "confirmed",
                "comment": "Late arrival"
            }
        }


class BookingUpdateIn(BaseModel):
    room_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_contact: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    price: Optional[float] = None
    status: Optional[BookingStatus] = None
    comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": 102,
                "guest_name": "Jane Smith",
                "start_date": "2025-10-08",
                "end_date": "2025-10-11",
                "status": "checked_in",
                "comment": "Extended stay by 1 night"
            }
        }


# ==== Helpers ====

def require_user(request: Request, db: Session) -> User:
    uid = get_current_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).get(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ==== Auth Endpoints ====

@router.post("/auth/login", response_model=UserOut)
def api_login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    set_session(response, user.id)
    return user


@router.get("/auth/me", response_model=UserOut)
def api_me(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return user


@router.get("/homestay", response_model=HomestayOut | None)
def api_homestay(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user.homestay_id:
        return None
    hs = db.query(Homestay).get(user.homestay_id)
    return hs


# ==== Rooms ====
@router.get("/rooms", response_model=List[RoomOut])
def api_rooms(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user.homestay_id:
        return []
    rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return rooms


# ==== Bookings ====
@router.get("/bookings", response_model=List[BookingOut])
def api_bookings(request: Request, db: Session = Depends(get_db), start: Optional[date] = None, end: Optional[date] = None, room_id: Optional[int] = None):
    user = require_user(request, db)
    try:
        run_auto_checkout(db)
    except Exception:
        pass
    q = db.query(Booking)
    # limit to user's homestay rooms
    if user.homestay_id:
        room_ids = [r.id for r in db.query(Room).filter(Room.homestay_id == user.homestay_id).all()]
        if room_ids:
            q = q.filter(Booking.room_id.in_(room_ids))
        else:
            return []
    if room_id:
        q = q.filter(Booking.room_id == room_id)
    if start:
        q = q.filter(Booking.end_date > start)
    if end:
        q = q.filter(Booking.start_date < end)
    return q.order_by(Booking.start_date.desc()).all()


@router.post("/bookings", response_model=BookingOut, status_code=201)
def api_create_booking(request: Request, payload: BookingCreateIn, db: Session = Depends(get_db)):
    user = require_user(request, db)
    room = db.query(Room).get(payload.room_id)
    if not room or room.homestay_id != user.homestay_id:
        raise HTTPException(status_code=404, detail="Room not found")
    s = payload.start_date
    e = payload.end_date
    if e <= s:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    conflicts = db.query(Booking).filter(Booking.room_id == payload.room_id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        raise HTTPException(status_code=409, detail="Conflict: overlapping booking exists")
    if getattr(room, "ota_ical_url", None):
        try:
            ota_events = fetch_ota_events(room.ota_ical_url)
            if overlaps_ota(ota_events, s, e):
                raise HTTPException(status_code=409, detail="Conflict: overlaps external OTA calendar")
        except Exception:
            pass
    b = Booking(
        room_id=payload.room_id,
        guest_name=payload.guest_name.strip(),
        guest_contact=(payload.guest_contact or "").strip(),
        start_date=s,
        end_date=e,
        price=payload.price,
        status=payload.status,
        comment=(payload.comment or None),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def api_update_booking(request: Request, booking_id: int, payload: BookingUpdateIn, db: Session = Depends(get_db)):
    user = require_user(request, db)
    b = db.query(Booking).get(booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    room = db.query(Room).get(b.room_id)
    if not room or room.homestay_id != user.homestay_id:
        raise HTTPException(status_code=404, detail="Not found")

    # Apply updates to a temp view to validate conflicts
    new_room_id = payload.room_id if payload.room_id is not None else b.room_id
    new_room = db.query(Room).get(new_room_id)
    if not new_room or new_room.homestay_id != user.homestay_id:
        raise HTTPException(status_code=404, detail="Room not found")

    s = payload.start_date if payload.start_date is not None else b.start_date
    e = payload.end_date if payload.end_date is not None else b.end_date
    if e <= s:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    conflicts = db.query(Booking).filter(Booking.room_id == new_room_id, Booking.id != b.id, Booking.start_date < e, Booking.end_date > s).all()
    if conflicts:
        raise HTTPException(status_code=409, detail="Conflict: overlapping booking exists")
    if getattr(new_room, "ota_ical_url", None):
        try:
            ota_events = fetch_ota_events(new_room.ota_ical_url)
            if overlaps_ota(ota_events, s, e):
                raise HTTPException(status_code=409, detail="Conflict: overlaps external OTA calendar")
        except Exception:
            pass

    # Persist changes
    b.room_id = new_room_id
    if payload.guest_name is not None:
        b.guest_name = payload.guest_name.strip()
    if payload.guest_contact is not None:
        b.guest_contact = payload.guest_contact.strip()
    b.start_date = s
    b.end_date = e
    if payload.price is not None:
        b.price = payload.price
    if payload.status is not None:
        b.status = payload.status
    if payload.comment is not None:
        b.comment = payload.comment.strip() or None

    db.commit()
    db.refresh(b)
    return b


@router.delete("/bookings/{booking_id}", status_code=204)
def api_delete_booking(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    b = db.query(Booking).get(booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    room = db.query(Room).get(b.room_id)
    if not room or room.homestay_id != user.homestay_id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(b)
    db.commit()
    return Response(status_code=204)
