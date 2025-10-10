import secrets
import json
from urllib import request as urlrequest
from urllib.parse import urlencode
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Form, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Plan, Subscription
from ..security import hash_password, verify_password, set_session, clear_session
from ..config import settings
from ..limiter import limiter
from ..services.mail import send_verification_email, send_password_reset_email, send_invitation_email
from ..templating import templates

router = APIRouter(prefix="/auth", tags=["auth"])

def _verify_recaptcha(token: str | None, remote_ip: str | None) -> tuple[bool, dict]:
    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    if not secret or not getattr(settings, "RECAPTCHA_SITE_KEY", ""):
        return True, {"skipped": True}
    if not token:
        return False, {"error": "missing-token"}
    data = urlencode({"secret": secret, "response": token, "remoteip": remote_ip or ""}).encode()
    try:
        req = urlrequest.Request("https://www.google.com/recaptcha/api/siteverify", data=data)
        with urlrequest.urlopen(req, timeout=5) as resp:
            payload = resp.read()
            res = json.loads(payload.decode("utf-8"))
            return bool(res.get("success")), res
    except Exception as e:
        if getattr(settings, "DEBUG", False):
            return True, {"debug": True, "exception": str(e)}
        return False, {"exception": str(e)}

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    error = request.query_params.get("error")
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request, 
            "error": error, 
            "msg": msg, 
            "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            "recaptcha_version": settings.RECAPTCHA_VERSION,
            "recaptcha_action": "login",
        },
    )

@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, email: str = Form(...), password: str = Form(...), g_recaptcha_response: str | None = Form(None, alias="g-recaptcha-response"), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    ok, res = _verify_recaptcha(g_recaptcha_response, client_ip)
    if ok and settings.RECAPTCHA_VERSION == "v3":
        expected_action = "login"
        min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
        if res.get("action") != expected_action or res.get("score", 0) < min_score:
            ok = False

    if not ok:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "reCAPTCHA verification failed. Please try again.", "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY, "recaptcha_version": settings.RECAPTCHA_VERSION, "recaptcha_action": "login"},
            status_code=400,
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password.", "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY, "recaptcha_version": settings.RECAPTCHA_VERSION, "recaptcha_action": "login"},
            status_code=400,
        )
    
    if not user.is_verified:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Please verify your email address before logging in.", "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY, "recaptcha_version": settings.RECAPTCHA_VERSION, "recaptcha_action": "login"},
            status_code=400,
        )

    redirect = RedirectResponse(url="/app", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request, "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY, "recaptcha_version": settings.RECAPTCHA_VERSION, "recaptcha_action": "register"})

@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(request: Request, background_tasks: BackgroundTasks, email: str = Form(...), password: str = Form(...), g_recaptcha_response: str | None = Form(None, alias="g-recaptcha-response"), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    ok, res = _verify_recaptcha(g_recaptcha_response, client_ip)
    if ok and settings.RECAPTCHA_VERSION == "v3":
        expected_action = "register"
        min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
        if res.get("action") != expected_action or res.get("score", 0) < min_score:
            ok = False

    if not ok:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "reCAPTCHA verification failed. Please try again.", "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY, "recaptcha_version": settings.RECAPTCHA_VERSION, "recaptcha_action": "register"},
            status_code=400,
        )

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        return RedirectResponse(url="/auth/login?error=Email+already+registered.", status_code=303)

    token = secrets.token_urlsafe(32)
    user = User(
        email=email, 
        hashed_password=hash_password(password),
        is_verified=False,
        verification_token=token
    )
    db.add(user)
    db.flush() # Flush to get the user ID

    # Assign free plan by default
    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    if free_plan:
        sub = Subscription(owner_id=user.id, plan_id=free_plan.id)
        db.add(sub)
    
    db.commit()

    background_tasks.add_task(send_verification_email, email, token)

    return templates.TemplateResponse("auth/verify_email.html", {"request": request, "email": email})

@router.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        return RedirectResponse(url="/auth/login?error=Invalid+verification+token.", status_code=303)

    user.is_verified = True
    user.verification_token = None
    db.commit()

    redirect = RedirectResponse(url="/app?msg=Email+verified+successfully!", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.get("/accept-invitation")
def accept_invitation_form(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.invitation_token == token).first()
    if not user or user.is_verified:
        return RedirectResponse(url="/auth/login?error=Invalid+or+expired+invitation+token.", status_code=303)
    
    return templates.TemplateResponse("auth/accept_invitation.html", {"request": request, "token": token})

@router.post("/accept-invitation")
def accept_invitation(request: Request, token: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.invitation_token == token).first()
    if not user or user.is_verified:
        return templates.TemplateResponse("auth/accept_invitation.html", {"request": request, "token": token, "error": "Invalid or expired invitation token."})

    if password != confirm_password:
        return templates.TemplateResponse("auth/accept_invitation.html", {"request": request, "token": token, "error": "Passwords do not match."})

    user.hashed_password = hash_password(password)
    user.is_verified = True
    user.invitation_token = None
    db.commit()

    redirect = RedirectResponse(url="/app?msg=Invitation+accepted!+Welcome+to+the+team.", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request):
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(request: Request, background_tasks: BackgroundTasks, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        background_tasks.add_task(send_password_reset_email, user.email, token)
    
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request, "message": "If an account with that email exists, we have sent a password reset link."})

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == token).first()
    if not user or user.password_reset_expires_at < datetime.utcnow():
        return RedirectResponse(url="/auth/login?error=Invalid+or+expired+password+reset+token.", status_code=303)
    
    return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token})

@router.post("/reset-password")
def reset_password(request: Request, token: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == token).first()
    if not user or user.password_reset_expires_at < datetime.utcnow():
        return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token, "error": "Invalid or expired password reset token."})

    if password != confirm_password:
        return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token, "error": "Passwords do not match."})

    user.hashed_password = hash_password(password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    user.is_verified = True # Also verify user if they came through this flow
    db.commit()

    redirect = RedirectResponse(url="/app?msg=Password+reset+successfully!", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.post("/logout")
def logout():
    redirect = RedirectResponse(url="/auth/login?msg=You+have+been+logged+out.", status_code=303)
    clear_session(redirect)
    return redirect
