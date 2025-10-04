from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Homestay, Subscription, SubscriptionStatus
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
