from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Homestay, Room, Booking, BookingStatus, Plan, Subscription
from ..security import get_current_user_id, set_session, verify_password, clear_session
from ..services.auto_checkout import run_auto_checkout
from ..services.ical import fetch_ota_events, overlaps_ota
from ..limiter import limiter
from ..config import settings

router = APIRouter(prefix="/api/v1", tags=["mobile-api"])

# ==== Schemas ====

class PlanOut(BaseModel):
    id: int
    name: str
    price_monthly: float
    price_yearly: float
    room_limit: int
    user_limit: int

    class Config:
        from_attributes = True

class SubscriptionOut(BaseModel):
    plan: PlanOut
    status: str
    expires_at: Optional[date] = None

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: str
    role: str
    homestay_id: int | None = None
    currency: str
    subscription: Optional[SubscriptionOut] = None

    class Config:
        from_attributes = True

class HomestayOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class RoomOut(BaseModel):
    id: int
    name: str
    capacity: Optional[int] = None
    default_rate: Optional[float] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

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

class LoginIn(BaseModel):
    email: str
    password: str

class BookingCreateIn(BaseModel):
    room_id: int
    guest_name: str
    guest_contact: Optional[str] = ""
    start_date: date
    end_date: date
    price: Optional[float] = None
    status: BookingStatus = Field(default=BookingStatus.CONFIRMED)
    comment: Optional[str] = None

class BookingUpdateIn(BaseModel):
    room_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_contact: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    price: Optional[float] = None
    status: Optional[BookingStatus] = None
    comment: Optional[str] = None

class SelectHomestayIn(BaseModel):
    homestay_id: int

# ==== Helpers ====

def require_user(request: Request, db: Session) -> User:
    uid = get_current_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).get(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ==== Auth & User Endpoints ====

@router.post("/auth/login", response_model=UserOut)
@limiter.limit(settings.RATE_LIMIT_AUTH_API)
def api_login(request: Request, payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    set_session(response, user.id)
    return user

@router.post("/auth/logout")
def api_logout(response: Response):
    clear_session(response)
    return {"ok": True}

@router.get("/auth/me", response_model=UserOut)
def api_me(request: Request, db: Session = Depends(get_db)):
    return require_user(request, db)

# ==== Plans & Homestays ====

@router.get("/plans", response_model=List[PlanOut])
def api_get_plans(db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_monthly.asc()).all()

@router.get("/homestays", response_model=List[HomestayOut])
def api_get_homestays(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return db.query(Homestay).filter(Homestay.owner_id == user.id).all()

@router.get("/homestay", response_model=HomestayOut | None)
def api_homestay(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user.homestay_id:
        return None
    return db.query(Homestay).get(user.homestay_id)

@router.post("/homestay/select", response_model=UserOut)
def api_select_homestay(request: Request, payload: SelectHomestayIn, db: Session = Depends(get_db)):
    user = require_user(request, db)
    hs = db.query(Homestay).get(payload.homestay_id)
    if not hs or hs.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Homestay not found")
    user.homestay_id = hs.id
    db.commit()
    db.refresh(user)
    return user

# ==== Rooms ====
@router.get("/rooms", response_model=List[RoomOut])
def api_rooms(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user.homestay_id:
        return []
    return db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()

# ==== Bookings ====
@router.get("/bookings", response_model=List[BookingOut])
def api_bookings(request: Request, db: Session = Depends(get_db), start: Optional[date] = None, end: Optional[date] = None, room_id: Optional[int] = None):
    user = require_user(request, db)
    try:
        run_auto_checkout(db)
    except Exception:
        db.rollback()
    q = db.query(Booking)
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
    conflicts = db.query(Booking).filter(Booking.room_id == payload.room_id, Booking.id != None, Booking.start_date < e, Booking.end_date > s).all()
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
        status=payload.status.value,
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
        b.status = payload.status.value
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
