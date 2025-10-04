from datetime import date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Homestay, Room
from ..security import get_current_user_id

router = APIRouter(tags=["app"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/app", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    user = db.query(User).get(uid)
    rooms = []
    if user and user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "rooms": rooms, "today": date.today()})
