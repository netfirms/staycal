import calendar as cal
from datetime import date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Homestay, Room, Booking, BookingStatus, Plan
from ..config import settings
from ..templating import templates

router = APIRouter(tags=["public"])

@router.get("/config")
def get_firebase_config():
    """Exposes client-side Firebase configuration."""
    firebase_config = {
        "apiKey": settings.FIREBASE_API_KEY,
        "authDomain": settings.FIREBASE_AUTH_DOMAIN,
        "projectId": settings.FIREBASE_PROJECT_ID,
        "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
        "appId": settings.FIREBASE_APP_ID,
        "measurementId": settings.FIREBASE_MEASUREMENT_ID,
    }
    # Filter out any keys that are not set, so they are not sent to the client.
    client_config = {k: v for k, v in firebase_config.items() if v}
    return JSONResponse(content=client_config)

@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_monthly.asc()).all()
    return templates.TemplateResponse("landing.html", {"request": request, "plans": plans})

@router.get("/public/{homestay_id}", response_class=HTMLResponse)
def public_property(request: Request, homestay_id: int, room_id: int | None = None, year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    hs = db.query(Homestay).get(homestay_id)
    if not hs:
        return HTMLResponse("<h2>Property not found</h2>", status_code=404)
    rooms = db.query(Room).filter(Room.homestay_id == hs.id).order_by(Room.name.asc()).all()
    if not rooms:
        return templates.TemplateResponse("public/property.html", {"request": request, "homestay": hs, "rooms": [], "year": date.today().year, "month": date.today().month, "days": 0, "bookings": [], "room_id": None, "first_wd": 0, "weekdays": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], "month_label": "", "today_str": date.today().isoformat()})
    # Select room
    if not room_id:
        room_id = rooms[0].id
    # Resolve month/year
    today = date.today()
    year = year or today.year
    month = month or today.month
    # Compute calendar meta
    first_wd, days = cal.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, days)
    bookings = db.query(Booking).filter(Booking.room_id == room_id, Booking.start_date <= end, Booking.end_date >= start).all()
    ctx = {
        "request": request,
        "homestay": hs,
        "rooms": rooms,
        "room_id": room_id,
        "year": year,
        "month": month,
        "days": days,
        "bookings": bookings,
        "first_wd": first_wd,
        "weekdays": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        "month_label": f"{cal.month_name[month]} {year}",
        "today_str": today.isoformat(),
    }
    return templates.TemplateResponse("public/property.html", ctx)

@router.get("/public/calendar/events")
def public_calendar_events(room_id: int, start: str, end: str, db: Session = Depends(get_db)):
    """Return bookings for a room within a given range (public, read-only)."""
    # Parse dates
    try:
        start_date = date.fromisoformat(start[:10])
        end_date = date.fromisoformat(end[:10])
    except Exception:
        # Return empty list on bad params (keep public endpoint permissive)
        return JSONResponse([], status_code=200)

    bookings = (
        db.query(Booking)
        .filter(
            Booking.room_id == room_id,
            Booking.start_date < end_date,
            Booking.end_date > start_date,
        )
        .all()
    )

    def color_for(status: BookingStatus) -> str:
        # Public view: always show internal bookings as orange for privacy/consistency
        return "#fdba74"  # orange-300

    def _public_title(_: str | None) -> str:
        # Public view should not display guest names; use a neutral label
        return "Not available"

    events = [
        {
            "id": b.id,
            "title": _public_title(b.guest_name),
            "start": b.start_date.isoformat(),
            "end": b.end_date.isoformat(),
            "allDay": True,
            "color": color_for(b.status),
        }
        for b in bookings
    ]

    # Append OTA (external) events if room has an iCal URL
    room = db.query(Room).get(room_id)
    if room and getattr(room, "ota_ical_url", None):
        try:
            from ..services.ical import fetch_ota_events
            ota_list = fetch_ota_events(room.ota_ical_url)
            for ev in ota_list:
                s = ev.get("start_date")
                e = ev.get("end_date")
                title = ev.get("title") or "OTA"
                if not s or not e:
                    continue
                if s < end_date and e > start_date:
                    events.append({
                        "id": f"ota-{s.isoformat()}-{e.isoformat()}",
                        "title": f"OTA: {title}",
                        "start": s.isoformat(),
                        "end": e.isoformat(),
                        "allDay": True,
                        "color": "#fdba74",  # orange-300
                    })
        except Exception:
            pass

    return JSONResponse(events)
