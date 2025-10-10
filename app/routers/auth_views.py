import secrets
import json
from urllib import request as urlrequest
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Form, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Plan, Subscription
from ..security import hash_password, verify_password, set_session, clear_session
from ..config import settings
from ..limiter import limiter
from ..services.mail import send_verification_email
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
    if not user or not verify_password(password, user.hashed_password):
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

@router.post("/logout")
def logout():
    redirect = RedirectResponse(url="/auth/login?msg=You+have+been+logged+out.", status_code=303)
    clear_session(redirect)
    return redirect
