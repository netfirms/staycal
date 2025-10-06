from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import hash_password, verify_password, set_session, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    # Pass optional messages into the template for nicer UI feedback
    error = request.query_params.get("error")
    msg = request.query_params.get("msg")
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": error, "msg": msg})

@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        # Re-render login page with friendly error instead of raising HTTPException
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password. Please try again."},
            status_code=400,
        )
    redirect = RedirectResponse(url="/app", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        # Keep error simple for now; registration UI can be improved later
        return RedirectResponse(url="/auth/login?error=Email%20already%20registered%2E%20Please%20sign%20in%20instead%2E", status_code=303)
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    redirect = RedirectResponse(url="/app", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.post("/logout")
def logout():
    redirect = RedirectResponse(url="/auth/login?msg=You%20have%20been%20logged%20out.", status_code=303)
    clear_session(redirect)
    return redirect
