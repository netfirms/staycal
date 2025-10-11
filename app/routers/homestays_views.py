import secrets
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Homestay, Room
from ..security import require_user, hash_password
from ..services.media import save_image
from ..templating import templates

router = APIRouter(prefix="/app/homestays", tags=["homestays"])

@router.get("/", response_class=HTMLResponse)
def homestays_index(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    owned: list[Homestay] = db.query(Homestay).filter(Homestay.owner_id == user.id).order_by(Homestay.created_at.desc()).all()
    return templates.TemplateResponse("homestays/list.html", {"request": request, "user": user, "homestays": owned})

@router.get("/new", response_class=HTMLResponse)
def homestays_new_form(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse("homestays/edit.html", {"request": request, "user": user, "homestay": None})

@router.post("/")
async def homestays_create(request: Request, user: User = Depends(require_user), name: str = Form(...), address: str = Form(""), set_active: bool = Form(False), image: UploadFile | None = File(None), db: Session = Depends(get_db)):
    if user.role not in ("owner", "admin"):
        return HTMLResponse("<h2>Forbidden: Only owners can create properties.</h2>", status_code=403)
    
    img_url = None
    if image and image.filename:
        data = await image.read()
        img_url = save_image(data, image.filename, folder="staycal/homestays")
        
    hs = Homestay(owner_id=user.id, name=name.strip(), address=address.strip(), image_url=img_url)
    db.add(hs)
    db.commit()
    db.refresh(hs)
    
    # Set as active if it's their first property or if they checked the box
    if set_active or not user.homestay_id:
        user.homestay_id = hs.id
        db.commit()
        
    return RedirectResponse(url="/app/homestays/", status_code=303)

@router.get("/{homestay_id}/edit", response_class=HTMLResponse)
def homestays_edit_form(request: Request, homestay_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    hs = db.query(Homestay).get(homestay_id)
    if not hs or hs.owner_id != user.id:
        return HTMLResponse("<h2>Property not found or not authorized</h2>", status_code=404)
    return templates.TemplateResponse("homestays/edit.html", {"request": request, "user": user, "homestay": hs})

@router.post("/{homestay_id}/edit")
async def homestays_edit(request: Request, homestay_id: int, user: User = Depends(require_user), name: str = Form(...), address: str = Form(""), image: UploadFile | None = File(None), db: Session = Depends(get_db)):
    hs = db.query(Homestay).get(homestay_id)
    if not hs or hs.owner_id != user.id:
        return HTMLResponse("<h2>Property not found or not authorized</h2>", status_code=404)
        
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
def homestays_delete(request: Request, homestay_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    hs = db.query(Homestay).get(homestay_id)
    if not hs or hs.owner_id != user.id:
        return HTMLResponse("<h2>Property not found or not authorized</h2>", status_code=404)
        
    # If user has this as active, unset it
    if user.homestay_id == hs.id:
        user.homestay_id = None
    db.delete(hs)
    db.commit()
    return RedirectResponse(url="/app/homestays/", status_code=303)

@router.post("/{homestay_id}/set_active")
def homestays_set_active(request: Request, homestay_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    hs = db.query(Homestay).get(homestay_id)
    if not hs:
        return HTMLResponse("<h2>Property not found</h2>", status_code=404)
    
    # Allow if user owns it, or if user is staff assigned to it
    if hs.owner_id != user.id and user.homestay_id != hs.id:
        return HTMLResponse("<h2>Not authorized to set this property as active</h2>", status_code=403)
        
    user.homestay_id = hs.id
    db.commit()
    return RedirectResponse(url="/app", status_code=303)
