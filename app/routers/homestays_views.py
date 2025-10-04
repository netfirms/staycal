from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Homestay, Room
from ..security import get_current_user_id

router = APIRouter(prefix="/app/homestays", tags=["homestays"])
templates = Jinja2Templates(directory="app/templates")


def require_user(request: Request, db: Session) -> User | None:
    uid = get_current_user_id(request)
    if not uid:
        return None
    return db.query(User).get(uid)


@router.get("/", response_class=HTMLResponse)
def homestays_index(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    owned: list[Homestay] = db.query(Homestay).filter(Homestay.owner_id == user.id).order_by(Homestay.created_at.desc()).all()
    current: Homestay | None = None
    rooms_count: int | None = None
    if user.homestay_id:
        current = db.query(Homestay).get(user.homestay_id)
        if current:
            rooms_count = db.query(Room).filter(Room.homestay_id == current.id).count()
    return templates.TemplateResponse(
        "homestays/index.html",
        {"request": request, "user": user, "owned": owned, "current": current, "rooms_count": rooms_count},
    )


@router.get("/new", response_class=HTMLResponse)
def homestays_new_form(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("homestays/edit.html", {"request": request, "user": user, "homestay": None})


@router.post("/")
def homestays_create(request: Request, name: str = Form(...), address: str = Form(""), set_active: bool = Form(False), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    # Only allow owners to create; if not owner, upgrade role minimally for MVP
    if user.role not in ("owner", "admin"):
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    hs = Homestay(owner_id=user.id, name=name.strip(), address=address.strip())
    db.add(hs)
    db.commit()
    db.refresh(hs)
    # Optionally set as active
    if set_active:
        user.homestay_id = hs.id
        db.commit()
    return RedirectResponse(url="/app/homestays/", status_code=303)


@router.get("/{homestay_id}/edit", response_class=HTMLResponse)
def homestays_edit_form(request: Request, homestay_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs or (hs.owner_id != user.id and user.role != "admin"):
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    return templates.TemplateResponse("homestays/edit.html", {"request": request, "user": user, "homestay": hs})


@router.post("/{homestay_id}/edit")
def homestays_edit(request: Request, homestay_id: int, name: str = Form(...), address: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs or (hs.owner_id != user.id and user.role != "admin"):
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    hs.name = name.strip()
    hs.address = address.strip()
    db.commit()
    return RedirectResponse(url="/app/homestays/", status_code=303)


@router.post("/{homestay_id}/delete")
def homestays_delete(request: Request, homestay_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs or (hs.owner_id != user.id and user.role != "admin"):
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    # If user has this as active, unset it
    if user.homestay_id == hs.id:
        user.homestay_id = None
    db.delete(hs)
    db.commit()
    return RedirectResponse(url="/app/homestays/", status_code=303)


@router.post("/{homestay_id}/set-active")
def homestays_set_active(request: Request, homestay_id: int, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    # Allow if user owns it, or if user is staff assigned to it
    if hs.owner_id != user.id and user.role != "admin":
        # If staff, allow only if already assigned to this homestay
        if user.homestay_id != hs.id:
            return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    user.homestay_id = hs.id
    db.commit()
    # After setting active, guide to rooms
    return RedirectResponse(url="/app", status_code=303)
