from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import get_current_user_id, verify_password, hash_password
from ..templating import templates
from ..services.currency import CURRENCY_SYMBOLS

router = APIRouter(prefix="/app/settings", tags=["settings"])

@router.get("/", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user = db.query(User).get(uid)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "available_currencies": CURRENCY_SYMBOLS.keys(),
        },
    )

@router.post("/currency")
def save_currency(request: Request, db: Session = Depends(get_db), currency: str = Form(...)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user = db.query(User).get(uid)
    if currency in CURRENCY_SYMBOLS:
        user.currency = currency
        db.commit()
    
    return RedirectResponse(url="/app/settings", status_code=303)

@router.post("/password")
def change_password(request: Request, db: Session = Depends(get_db), current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user = db.query(User).get(uid)
    
    if not verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse("settings.html", {"request": request, "user": user, "available_currencies": CURRENCY_SYMBOLS.keys(), "error": "Incorrect current password."})
    
    if new_password != confirm_password:
        return templates.TemplateResponse("settings.html", {"request": request, "user": user, "available_currencies": CURRENCY_SYMBOLS.keys(), "error": "New passwords do not match."})
    
    user.hashed_password = hash_password(new_password)
    db.commit()
    
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "available_currencies": CURRENCY_SYMBOLS.keys(), "message": "Password updated successfully."})
