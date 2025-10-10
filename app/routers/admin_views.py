from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
import os
from ..db import get_db
from ..models import User, Homestay, Subscription, SubscriptionStatus, Room, Booking, BookingStatus, UserRole, Plan
from ..security import get_current_user_id, hash_password, verify_password
from ..config import settings
from ..services.media import _ensure_cloudinary_configured
from ..templating import templates
from ..services.currency import CURRENCY_SYMBOLS

router = APIRouter(prefix="/admin", tags=["admin"])

# Dependency to protect admin routes
def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    uid = get_current_user_id(request)
    if not uid:
        raise HTTPException(status_code=307, headers={"Location": "/admin/login"})
    
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return user

@router.get("/login", response_class=HTMLResponse)
def admin_login_form(request: Request):
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    version = "v3"
    action = "admin_login"
    return templates.TemplateResponse("admin/login.html", {"request": request, "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action})


def _verify_recaptcha_admin(token: str | None, remote_ip: str | None) -> tuple[bool, dict]:
    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    if not secret:
        return True, {"skipped": True}
    if not token:
        return False, {"error": "missing-token"}
    from urllib.parse import urlencode
    from urllib import request as urlrequest
    import json
    data = urlencode({"secret": secret, "response": token, "remoteip": remote_ip or ""}).encode()
    try:
        req = urlrequest.Request("https://www.google.com/recaptcha/api/siteverify", data=data)
        with urlrequest.urlopen(req, timeout=5) as resp:
            payload = resp.read()
            res = json.loads(payload.decode("utf-8"))
            return bool(res.get("success")), res
    except Exception as e:
        if getattr(settings, "DEBUG", False):
            return True, {"debug": True, "exception": str(e)}
        return False, {"exception": str(e)}


@router.post("/login")
def admin_login(request: Request, email: str = Form(...), password: str = Form(...), g_recaptcha_response: str | None = Form(None, alias="g-recaptcha-response"), db: Session = Depends(get_db)):
    # reCAPTCHA (optional, enforced if keys configured)
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    version = "v3"
    action = "admin_login"
    if site_key and secret_key:
        client_ip = request.client.host if request.client else None
        ok, res = _verify_recaptcha_admin(g_recaptcha_response, client_ip)
        if ok:
            expected_action = "admin_login"
            min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
            if res.get("action") and res.get("action") != expected_action:
                ok = False
            score_val = res.get("score")
            if score_val is not None:
                try:
                    score = float(score_val)
                except Exception:
                    score = None
                if score is not None and score < min_score:
                    ok = False
        if not ok:
            return templates.TemplateResponse(
                "admin/login.html",
                {"request": request, "error": "reCAPTCHA verification failed. Please try again.", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
                status_code=400,
            )
    user = db.query(User).filter(User.email == email).first()
    from ..security import verify_password, set_session
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid email or password", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
            status_code=400,
        )
    if user.role != "admin":
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "You are not authorized to access the admin dashboard.", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
            status_code=403,
        )
    redirect = RedirectResponse(url="/admin", status_code=303)
    set_session(redirect, user.id)
    return redirect


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    # Base lists used by existing dashboard tables
    users = db.query(User).all()
    homestays = db.query(Homestay).all()
    subs = db.query(Subscription).all()

    # --- Analytics Calculations ---
    today = date.today()
    month_start = date(today.year, today.month, 1)
    days_in_month = (date(today.year, today.month + 1, 1) - month_start).days if today.month < 12 else 31

    users_count = len(users)
    homestays_count = len(homestays)
    rooms_count = db.query(func.count(Room.id)).scalar() or 0
    bookings_count = db.query(func.count(Booking.id)).scalar() or 0

    # Today check-ins and check-outs
    checkins_today = db.query(func.count(Booking.id)).filter(Booking.start_date == today, Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value])).scalar() or 0
    checkouts_today = db.query(func.count(Booking.id)).filter(Booking.end_date == today, Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value, BookingStatus.CHECKED_OUT.value])).scalar() or 0

    # Monthly metrics
    monthly_bookings = db.query(func.count(Booking.id)).filter(Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month))).scalar() or 0
    monthly_revenue = db.query(func.coalesce(func.sum(Booking.price), 0)).filter(Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month)), Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value, BookingStatus.CHECKED_OUT.value])).scalar() or 0

    # Occupancy, ADR, RevPAR for the current month
    total_room_nights_in_month = rooms_count * days_in_month
    booked_nights_in_month = db.query(func.sum(Booking.end_date - Booking.start_date)).filter(Booking.start_date >= month_start, Booking.start_date < (month_start + timedelta(days=days_in_month)), Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value])).scalar() or 0

    occupancy_rate = (booked_nights_in_month / total_room_nights_in_month) * 100 if total_room_nights_in_month > 0 else 0
    adr = monthly_revenue / booked_nights_in_month if booked_nights_in_month > 0 else 0
    revpar = monthly_revenue / total_room_nights_in_month if total_room_nights_in_month > 0 else 0

    # Booking status distribution
    status_counts = {st.value: db.query(func.count(Booking.id)).filter(Booking.status == st.value).scalar() or 0 for st in BookingStatus}

    # Plan distribution
    plans = db.query(Plan).all()
    plan_counts = {p.name: db.query(func.count(Subscription.id)).filter(Subscription.plan_id == p.id).scalar() or 0 for p in plans}

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_bookings = db.query(Booking).order_by(Booking.created_at.desc()).limit(5).all()

    # User-specific analytics
    user_analytics = []
    for user in users:
        user_homestay_ids = [h.id for h in user.homestays_owned]
        user_room_ids = [r[0] for r in db.query(Room.id).filter(Room.homestay_id.in_(user_homestay_ids)).all()]
        user_total_revenue = db.query(func.coalesce(func.sum(Booking.price), 0)).filter(Booking.room_id.in_(user_room_ids)).scalar() or 0
        user_analytics.append({"user": user, "total_revenue": float(user_total_revenue), "homestay_count": len(user_homestay_ids), "room_count": len(user_room_ids)})

    analytics = {
        "users_count": users_count, "homestays_count": homestays_count, "rooms_count": rooms_count, "bookings_count": bookings_count,
        "checkins_today": checkins_today, "checkouts_today": checkouts_today, "monthly_bookings": monthly_bookings,
        "monthly_revenue": float(monthly_revenue), "status_counts": status_counts, "plan_counts": plan_counts,
        "recent_users": recent_users, "recent_bookings": recent_bookings, "today": today, "month_start": month_start,
        "user_analytics": user_analytics, "occupancy_rate": occupancy_rate, "adr": adr, "revpar": revpar,
    }

    subs_map = {s.owner_id: s for s in subs}

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request, "user": admin_user, "users": users, "homestays": homestays, "subs": subs, "subs_map": subs_map,
            "plans": plans, "SubscriptionStatus": SubscriptionStatus, "analytics": analytics, "available_currencies": CURRENCY_SYMBOLS.keys(),
        },
    )

@router.get("/settings", response_class=HTMLResponse)
def admin_settings_page(request: Request, admin_user: User = Depends(require_admin)):
    error = request.query_params.get("error")
    message = request.query_params.get("message")
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": admin_user,
            "available_currencies": CURRENCY_SYMBOLS.keys(),
            "error": error,
            "message": message,
        },
    )

@router.post("/settings/currency")
def admin_save_currency(request: Request, db: Session = Depends(get_db), admin_user: User = Depends(require_admin), currency: str = Form(...)):
    if currency in CURRENCY_SYMBOLS:
        admin_user.currency = currency
        db.commit()
    return RedirectResponse(url="/admin/settings?message=Currency+updated.", status_code=303)

@router.post("/settings/password")
def admin_change_password(request: Request, db: Session = Depends(get_db), admin_user: User = Depends(require_admin), current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    if not verify_password(current_password, admin_user.hashed_password):
        return RedirectResponse(url="/admin/settings?error=Incorrect+current+password.", status_code=303)
    
    if new_password != confirm_password:
        return RedirectResponse(url="/admin/settings?error=New+passwords+do+not+match.", status_code=303)
    
    admin_user.hashed_password = hash_password(new_password)
    db.commit()
    
    return RedirectResponse(url="/admin/settings?message=Password+updated+successfully.", status_code=303)

@router.get("/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    users = db.query(User).order_by(User.id.asc()).all()
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": users})

# ... (rest of the file is unchanged)
