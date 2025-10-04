from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from ..models import User, Homestay, Subscription, SubscriptionStatus, PlanName
from ..security import get_current_user_id

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    # naive check: require email contains '@admin' or role
    user = db.query(User).get(uid)
    if not user or user.role != "admin":
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    users = db.query(User).all()
    homestays = db.query(Homestay).all()
    subs = db.query(Subscription).all()
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "users": users, "homestays": homestays, "subs": subs})


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
