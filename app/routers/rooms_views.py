from fastapi import APIRouter, Depends, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Room
from ..security import get_current_user_id
from ..services.media import save_image
from ..templating import templates

router = APIRouter(prefix="/app/rooms", tags=["rooms"])

def require_user(request: Request, db: Session) -> User | None:
    uid = get_current_user_id(request)
    if not uid:
        return None
    return db.query(User).get(uid)

@router.get("/", response_class=HTMLResponse)
def rooms_index(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    rooms = []
    if user.homestay_id:
        rooms = db.query(Room).filter(Room.homestay_id == user.homestay_id).order_by(Room.name.asc()).all()
    return templates.TemplateResponse("rooms/index.html", {"request": request, "user": user, "rooms": rooms})

@router.get("/new", response_class=HTMLResponse)
def rooms_new(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("rooms/form.html", {"request": request, "user": user, "room": None, "mode": "new"})

@router.post("/new")
async def rooms_create(request: Request, db: Session = Depends(get_db), name: str = Form(...), capacity: int = Form(1), default_rate: float | None = Form(None), ota_ical_url: str | None = Form(None), image: UploadFile | None = File(None)):
    user = require_user(request, db)
    if not user or not user.homestay_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    img_url = None
    if image and image.filename:
        data = await image.read()
        img_url = save_image(data, image.filename, folder="staycal/rooms")
    room = Room(homestay_id=user.homestay_id, name=name, capacity=capacity, default_rate=default_rate, ota_ical_url=ota_ical_url, image_url=img_url)
    db.add(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)

@router.get("/{room_id}/edit", response_class=HTMLResponse)
def rooms_edit(request: Request, room_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Room not found</h2>", status_code=404)
    return templates.TemplateResponse("rooms/form.html", {"request": request, "user": user, "room": room, "mode": "edit"})

@router.post("/{room_id}/edit")
async def rooms_update(request: Request, room_id: int, db: Session = Depends(get_db), name: str = Form(...), capacity: int = Form(1), default_rate: float | None = Form(None), ota_ical_url: str | None = Form(None), image: UploadFile | None = File(None)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Room not found</h2>", status_code=404)
    room.name = name
    room.capacity = capacity
    room.default_rate = default_rate
    room.ota_ical_url = ota_ical_url
    if image and image.filename:
        data = await image.read()
        room.image_url = save_image(data, image.filename, folder="staycal/rooms")
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)

@router.post("/{room_id}/delete")
def rooms_delete(request: Request, room_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id != user.homestay_id:
        return HTMLResponse("<h2>Room not found</h2>", status_code=404)
    db.delete(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)
