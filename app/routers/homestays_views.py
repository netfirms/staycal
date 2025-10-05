import secrets
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Homestay, Room
from ..security import get_current_user_id, hash_password
from ..services.media import save_image

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
    staff: list[User] = []
    if user.homestay_id:
        current = db.query(Homestay).get(user.homestay_id)
        if current:
            rooms_count = db.query(Room).filter(Room.homestay_id == current.id).count()
            staff = db.query(User).filter(User.homestay_id == current.id).order_by(User.email.asc()).all()
    # Simple flash messages via query params (MVP)
    invited_email = request.query_params.get("email")
    temp_pwd = request.query_params.get("pwd")
    removed_user_id = request.query_params.get("removed")
    err = request.query_params.get("error")
    return templates.TemplateResponse(
        "homestays/index.html",
        {
            "request": request,
            "user": user,
            "owned": owned,
            "current": current,
            "rooms_count": rooms_count,
            "staff": staff,
            "invited_email": invited_email,
            "temp_pwd": temp_pwd,
            "removed_user_id": removed_user_id,
            "error": err,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def homestays_new_form(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("homestays/edit.html", {"request": request, "user": user, "homestay": None})


@router.post("/")
async def homestays_create(request: Request, name: str = Form(...), address: str = Form(""), set_active: bool = Form(False), image: UploadFile | None = File(None), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    # Only allow owners to create; if not owner, upgrade role minimally for MVP
    if user.role not in ("owner", "admin"):
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    img_url = None
    if image and image.filename:
        data = await image.read()
        img_url = save_image(data, image.filename, folder="staycal/homestays")
    hs = Homestay(owner_id=user.id, name=name.strip(), address=address.strip(), image_url=img_url)
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
async def homestays_edit(request: Request, homestay_id: int, name: str = Form(...), address: str = Form(""), image: UploadFile | None = File(None), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs or (hs.owner_id != user.id and user.role != "admin"):
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    hs.name = name.strip()
    hs.address = address.strip()
    if image and image.filename:
        data = await image.read()
        new_url = save_image(data, image.filename, folder="staycal/homestays")
        if new_url:
            hs.image_url = new_url
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


@router.post("/{homestay_id}/invite")
async def homestays_invite(request: Request, homestay_id: int, email: str = Form(...), db: Session = Depends(get_db)):
    me = require_user(request, db)
    if not me:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    if me.role != "admin" and hs.owner_id != me.id:
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)

    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        return RedirectResponse(url=f"/app/homestays/?error=invalid_email", status_code=303)

    existing = db.query(User).filter(User.email == email_norm).first()
    if existing:
        # Assign to this homestay; keep admin/owner roles intact, otherwise set as staff
        existing.homestay_id = hs.id
        if existing.role not in ("admin", "owner"):
            existing.role = "staff"
        db.commit()
        return RedirectResponse(url=f"/app/homestays/?email={email_norm}", status_code=303)
    else:
        temp_pwd = secrets.token_urlsafe(8)
        u = User(email=email_norm, hashed_password=hash_password(temp_pwd), role="staff", homestay_id=hs.id)
        db.add(u)
        db.commit()
        return RedirectResponse(url=f"/app/homestays/?email={email_norm}&pwd={temp_pwd}", status_code=303)


@router.post("/{homestay_id}/remove-staff")
def homestays_remove_staff(request: Request, homestay_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    me = require_user(request, db)
    if not me:
        return RedirectResponse(url="/auth/login", status_code=303)
    hs = db.query(Homestay).get(homestay_id)
    if not hs:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    if me.role != "admin" and hs.owner_id != me.id:
        return HTMLResponse("<h2>Forbidden</h2>", status_code=403)
    target = db.query(User).get(user_id)
    if not target or target.homestay_id != hs.id:
        return HTMLResponse("<h2>Not found</h2>", status_code=404)
    if target.id == hs.owner_id or target.role == "admin":
        return HTMLResponse("<h2>Cannot remove owner/admin</h2>", status_code=400)
    # If target is currently active on this homestay, detaching is fine
    target.homestay_id = None
    db.commit()
    return RedirectResponse(url=f"/app/homestays/?removed={target.id}", status_code=303)
