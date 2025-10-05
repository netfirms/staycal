from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import os
from ..db import get_db
from ..models import User, Homestay, Subscription, SubscriptionStatus, PlanName, Room, Booking, BookingStatus
from ..security import get_current_user_id
from ..config import settings
from ..services.media import _ensure_cloudinary_configured

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    # require admin role
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)

    # Base lists used by existing dashboard tables
    users = db.query(User).all()
    homestays = db.query(Homestay).all()
    subs = db.query(Subscription).all()

    # Analytics
    today = date.today()
    month_start = date(today.year, today.month, 1)
    # compute next month start
    next_month = today.month + 1
    next_year = today.year + 1 if next_month == 13 else today.year
    next_month = 1 if next_month == 13 else next_month
    next_month_start = date(next_year, next_month, 1)

    users_count = db.query(func.count(User.id)).scalar() or 0
    homestays_count = db.query(func.count(Homestay.id)).scalar() or 0
    rooms_count = db.query(func.count(Room.id)).scalar() or 0
    bookings_count = db.query(func.count(Booking.id)).scalar() or 0

    # Today check-ins and check-outs (simple definition)
    checkins_today = (
        db.query(func.count(Booking.id))
        .filter(Booking.start_date == today, Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]))
        .scalar()
        or 0
    )
    checkouts_today = (
        db.query(func.count(Booking.id))
        .filter(Booking.end_date == today, Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]))
        .scalar()
        or 0
    )

    # Current month metrics
    monthly_bookings = (
        db.query(func.count(Booking.id))
        .filter(Booking.start_date >= month_start, Booking.start_date < next_month_start)
        .scalar()
        or 0
    )
    monthly_revenue = (
        db.query(func.coalesce(func.sum(Booking.price), 0))
        .filter(
            Booking.start_date >= month_start,
            Booking.start_date < next_month_start,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]),
        )
        .scalar()
        or 0
    )

    # Booking status distribution
    status_counts = {}
    for st in BookingStatus:
        cnt = db.query(func.count(Booking.id)).filter(Booking.status == st).scalar() or 0
        status_counts[st.value] = cnt

    # Plan distribution (by current subscriptions)
    plan_counts = {p.value: 0 for p in PlanName}
    for p in PlanName:
        cnt = db.query(func.count(Subscription.id)).filter(Subscription.plan_name == p).scalar() or 0
        plan_counts[p.value] = cnt

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_bookings = db.query(Booking).order_by(Booking.start_date.desc()).limit(5).all()

    analytics = {
        "users_count": users_count,
        "homestays_count": homestays_count,
        "rooms_count": rooms_count,
        "bookings_count": bookings_count,
        "checkins_today": checkins_today,
        "checkouts_today": checkouts_today,
        "monthly_bookings": monthly_bookings,
        "monthly_revenue": float(monthly_revenue) if monthly_revenue is not None else 0.0,
        "status_counts": status_counts,
        "plan_counts": plan_counts,
        "recent_users": recent_users,
        "recent_bookings": recent_bookings,
        "today": today,
        "month_start": month_start,
    }

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "homestays": homestays,
            "subs": subs,
            "analytics": analytics,
        },
    )


@router.get("/plans", response_class=HTMLResponse)
def admin_plans(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    users = db.query(User).order_by(User.id.asc()).all()
    subs = db.query(Subscription).all()
    subs_map = {s.owner_id: s for s in subs}
    return templates.TemplateResponse(
        "admin/plans.html",
        {
            "request": request,
            "users": users,
            "subs_map": subs_map,
            "PlanName": PlanName,
            "SubscriptionStatus": SubscriptionStatus,
        },
    )


@router.post("/plans/save")
def admin_plans_save(
    request: Request,
    db: Session = Depends(get_db),
    owner_id: int = Form(...),
    plan_name: str = Form(...),
    status: str = Form(...),
    expires_at: str | None = Form(None),
):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    admin_user = db.query(User).get(uid)
    if not admin_user or admin_user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)

    target = db.query(User).get(owner_id)
    if not target:
        return HTMLResponse("<h2>User not found</h2>", status_code=404)

    # Get or create subscription for this owner
    sub = db.query(Subscription).filter(Subscription.owner_id == owner_id).first()
    if not sub:
        sub = Subscription(owner_id=owner_id)
        db.add(sub)

    # Coerce enums safely
    try:
        sub.plan_name = PlanName(plan_name)
    except Exception:
        sub.plan_name = PlanName.FREE
    try:
        sub.status = SubscriptionStatus(status)
    except Exception:
        sub.status = SubscriptionStatus.ACTIVE

    # Parse optional expires_at (date or datetime)
    dt = None
    if expires_at:
        try:
            # try date-only first
            if len(expires_at) == 10:
                dt = datetime.fromisoformat(expires_at + "T00:00:00")
            else:
                dt = datetime.fromisoformat(expires_at)
        except Exception:
            dt = None
    sub.expires_at = dt

    db.commit()
    return RedirectResponse(url="/admin/plans", status_code=303)


@router.get("/cloudinary", response_class=HTMLResponse)
def admin_cloudinary(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    current_url = getattr(settings, "CLOUDINARY_URL", "")
    ok = False
    try:
        ok = _ensure_cloudinary_configured()
    except Exception:
        ok = False
    return templates.TemplateResponse(
        "admin/cloudinary.html",
        {"request": request, "current_url": current_url, "configured": ok, "message": None, "error": None},
    )


@router.post("/cloudinary")
def admin_cloudinary_save(request: Request, db: Session = Depends(get_db), cloudinary_url: str = Form("") ):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)

    url = (cloudinary_url or "").strip()
    # update runtime settings and environment
    os.environ["CLOUDINARY_URL"] = url
    try:
        setattr(settings, "CLOUDINARY_URL", url)
    except Exception:
        pass

    ok = False
    msg = None
    err = None
    try:
        ok = _ensure_cloudinary_configured()
        msg = "Cloudinary configuration saved." if ok else None
        if not ok:
            err = "Failed to configure Cloudinary. Please verify the URL and try again."
    except Exception:
        ok = False
        err = "Failed to configure Cloudinary. Please verify the URL and try again."

    return templates.TemplateResponse(
        "admin/cloudinary.html",
        {"request": request, "current_url": url, "configured": ok, "message": msg, "error": err},
    )
