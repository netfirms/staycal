from fastapi import APIRouter, Depends, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Room
from ..security import require_user
from ..services.media import save_image
from ..templating import templates

router = APIRouter(prefix="/app/rooms", tags=["rooms"])

@router.get("/", response_class=HTMLResponse)
def rooms_index(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    rooms = []
    if user.homestays_owned:
        owned_homestay_ids = [h.id for h in user.homestays_owned]
        rooms = db.query(Room).filter(Room.homestay_id.in_(owned_homestay_ids)).order_by(Room.name.asc()).all()
    return templates.TemplateResponse("rooms/index.html", {"request": request, "user": user, "rooms": rooms})

@router.get("/new", response_class=HTMLResponse)
def rooms_new(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not user.homestay_id:
        # Redirect to create a homestay if they don't have one to add a room to.
        return RedirectResponse(url="/app/homestays/new?notice=create_property_first", status_code=303)
    return templates.TemplateResponse("rooms/form.html", {"request": request, "user": user, "room": None, "mode": "new"})

@router.post("/new")
async def rooms_create(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db), name: str = Form(...), capacity: int = Form(1), default_rate: float | None = Form(None), ota_ical_url: str | None = Form(None), image: UploadFile | None = File(None)):
    if not user.homestay_id:
        return HTMLResponse("<h2>No active property selected</h2>", status_code=400)
    
    # Authorization check: Ensure the active homestay is owned by the user
    if user.homestay_id not in [h.id for h in user.homestays_owned]:
        return HTMLResponse("<h2>Not authorized to add rooms to this property</h2>", status_code=403)

    img_url = None
    if image and image.filename:
        data = await image.read()
        img_url = save_image(data, image.filename, folder="staycal/rooms")
    room = Room(homestay_id=user.homestay_id, name=name, capacity=capacity, default_rate=default_rate, ota_ical_url=ota_ical_url, image_url=img_url)
    db.add(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)

@router.get("/{room_id}/edit", response_class=HTMLResponse)
def rooms_edit(request: Request, room_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id not in [h.id for h in user.homestays_owned]:
        return HTMLResponse("<h2>Room not found or not authorized</h2>", status_code=404)
    return templates.TemplateResponse("rooms/form.html", {"request": request, "user": user, "room": room, "mode": "edit"})

@router.post("/{room_id}/edit")
async def rooms_update(request: Request, room_id: int, user: User = Depends(require_user), db: Session = Depends(get_db), name: str = Form(...), capacity: int = Form(1), default_rate: float | None = Form(None), ota_ical_url: str | None = Form(None), image: UploadFile | None = File(None)):
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id not in [h.id for h in user.homestays_owned]:
        return HTMLResponse("<h2>Room not found or not authorized</h2>", status_code=404)
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
def rooms_delete(request: Request, room_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    room = db.query(Room).get(room_id)
    if not room or room.homestay_id not in [h.id for h in user.homestays_owned]:
        return HTMLResponse("<h2>Room not found or not authorized</h2>", status_code=404)
    db.delete(room)
    db.commit()
    return RedirectResponse(url="/app/rooms/", status_code=303)
