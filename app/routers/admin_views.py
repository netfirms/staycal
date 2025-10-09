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
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/admin/login", status_code=303)
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

    # Build a quick map of subscriptions by owner for inline plan management
    subs_map = {s.owner_id: s for s in subs}

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "homestays": homestays,
            "subs": subs,
            "subs_map": subs_map,
            "PlanName": PlanName,
            "SubscriptionStatus": SubscriptionStatus,
            "analytics": analytics,
            # Pricing for display/editing
            "pricing": {
                "basic_monthly": getattr(settings, "PLAN_BASIC_MONTHLY", 249),
                "basic_yearly": getattr(settings, "PLAN_BASIC_YEARLY", 2490),
                "pro_monthly": getattr(settings, "PLAN_PRO_MONTHLY", 699),
                "pro_yearly": getattr(settings, "PLAN_PRO_YEARLY", 6990),
            },
            "pricing_saved": request.query_params.get("pricing_saved"),
            "pricing_error": request.query_params.get("pricing_error"),
        },
    )


@router.get("/plans", response_class=HTMLResponse)
def admin_plans(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/admin/login", status_code=303)
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
    return_to: str | None = Form(None),
):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/admin/login", status_code=303)
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
    # Redirect back to the requested page (dashboard or plans)
    dest = (return_to or "").strip() if return_to else None
    if not dest:
        # fallback to Referer if provided
        dest = request.headers.get("referer")
    if not dest:
        dest = "/admin/plans"
    return RedirectResponse(url=dest, status_code=303)


@router.get("/cloudinary", response_class=HTMLResponse)
def admin_cloudinary(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/admin/login", status_code=303)
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
        return RedirectResponse(url="/admin/login", status_code=303)
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


@router.post("/pricing")
def admin_pricing_save(
    request: Request,
    db: Session = Depends(get_db),
    basic_monthly: str = Form(...),
    basic_yearly: str = Form(...),
    pro_monthly: str = Form(...),
    pro_yearly: str = Form(...),
):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/admin/login", status_code=303)
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)

    def _parse_float(s: str) -> float | None:
        try:
            v = float((s or "").strip())
            if v < 0:
                return None
            return v
        except Exception:
            return None

    bm = _parse_float(basic_monthly)
    by = _parse_float(basic_yearly)
    pm = _parse_float(pro_monthly)
    py = _parse_float(pro_yearly)

    if None in (bm, by, pm, py):
        return RedirectResponse(url="/admin?pricing_error=invalid", status_code=303)

    # Persist in environment and in-memory settings (runtime)
    os.environ["PLAN_BASIC_MONTHLY"] = str(bm)
    os.environ["PLAN_BASIC_YEARLY"] = str(by)
    os.environ["PLAN_PRO_MONTHLY"] = str(pm)
    os.environ["PLAN_PRO_YEARLY"] = str(py)
    try:
        setattr(settings, "PLAN_BASIC_MONTHLY", bm)
        setattr(settings, "PLAN_BASIC_YEARLY", by)
        setattr(settings, "PLAN_PRO_MONTHLY", pm)
        setattr(settings, "PLAN_PRO_YEARLY", py)
    except Exception:
        pass

    return RedirectResponse(url="/admin?pricing_saved=1", status_code=303)
