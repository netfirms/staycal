from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Room
from ..security import get_current_user_id

router = APIRouter(prefix="/app/rooms", tags=["rooms"])
templates = Jinja2Templates(directory="app/templates")


def require_user(request: Request, db: Session) -> User | None:
    uid = get_current_user_id(request)
    if not uid:
        return None
    user = db.query(User).get(uid)
    return user


@router.get("/", response_class=HTMLResponse)
def rooms_index(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    rooms = []
    if user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return templates.TemplateResponse("rooms/index.html", {"request": request, "user": user, "rooms": rooms})


@router.post("/")
def rooms_create(request: Request, name: str = Form(...), capacity: int = Form(2), default_rate: float | None = Form(None), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if not user.homestay_id:
        return HTMLResponse("<div>Please create/select a property first.</div>", status_code=400)
    room = Room(homestay_id=user.homestay_id, name=name.strip(), capacity=capacity, default_rate=default_rate)
    db.add(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)


@router.get("/{room_id}/edit", response_class=HTMLResponse)
def rooms_edit_form(request: Request, room_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    return templates.TemplateResponse("rooms/edit.html", {"request": request, "user": user, "room": room})


@router.post("/{room_id}/edit")
def rooms_edit(request: Request, room_id: int, name: str = Form(...), capacity: int = Form(2), default_rate: float | None = Form(None), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    room.name = name.strip()
    room.capacity = capacity
    room.default_rate = default_rate
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)


@router.post("/{room_id}/delete")
def rooms_delete(request: Request, room_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    db.delete(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)
