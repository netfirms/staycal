from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import hash_password, verify_password, set_session, clear_session
from ..config import settings
from ..limiter import limiter
import json
from urllib import request as urlrequest
from urllib.parse import urlencode

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    # Pass optional messages into the template for nicer UI feedback
    error = request.query_params.get("error")
    msg = request.query_params.get("msg")
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    version = "v3"
    action = getattr(settings, "RECAPTCHA_EXPECTED_ACTION", "login")
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error": error, "msg": msg, "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
    )


def _verify_recaptcha(token: str | None, remote_ip: str | None) -> tuple[bool, dict]:
    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    if not secret:
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
        # Fail open in DEBUG for usability
        if getattr(settings, "DEBUG", False):
            return True, {"debug": True, "exception": str(e)}
        return False, {"exception": str(e)}

@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, email: str = Form(...), password: str = Form(...), g_recaptcha_response: str | None = Form(None, alias="g-recaptcha-response"), db: Session = Depends(get_db)):
    # Check reCAPTCHA if configured (site key and secret must be set)
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    version = "v3"
    action = getattr(settings, "RECAPTCHA_EXPECTED_ACTION", "login")
    if site_key and secret_key:
        client_ip = request.client.host if request.client else None
        ok, res = _verify_recaptcha(g_recaptcha_response, client_ip)
        if ok:
            # Optional checks for v3 (score-based)
            expected_action = getattr(settings, "RECAPTCHA_EXPECTED_ACTION", "login")
            min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
            # Only enforce action if Google provided one
            if res.get("action") and res.get("action") != expected_action:
                ok = False
            # Only enforce score threshold if score is present in response
            score_val = res.get("score")
            if score_val is not None:
                try:
                    score = float(score_val)
                except Exception:
                    score = None
                if score is not None and score < min_score:
                    ok = False
        if not ok:
            return templates.TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "reCAPTCHA verification failed. Please try again.", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
                status_code=400,
            )
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        # Re-render login page with friendly error instead of raising HTTPException
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password. Please try again.", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
            status_code=400,
        )
    redirect = RedirectResponse(url="/app", status_code=303)
    set_session(redirect, user.id)
    return redirect

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    version = "v3"
    action = "register"
    return templates.TemplateResponse("auth/register.html", {"request": request, "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action})

@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register(request: Request, email: str = Form(...), password: str = Form(...), g_recaptcha_response: str | None = Form(None, alias="g-recaptcha-response"), db: Session = Depends(get_db)):
    # Enforce reCAPTCHA when configured
    site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")
    secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    version = "v3"
    action = "register"
    if site_key and secret_key:
        client_ip = request.client.host if request.client else None
        ok, res = _verify_recaptcha(g_recaptcha_response, client_ip)
        if ok:
            expected_action = "register"
            min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
            if res.get("action") and res.get("action") != expected_action:
                ok = False
            score_val = res.get("score")
            if score_val is not None:
                try:
                    score = float(score_val)
                except Exception:
                    score = None
                if score is not None and score < min_score:
                    ok = False
        if not ok:
            return templates.TemplateResponse(
                "auth/register.html",
                {"request": request, "error": "reCAPTCHA verification failed. Please try again.", "recaptcha_site_key": site_key, "recaptcha_version": version, "recaptcha_action": action},
                status_code=400,
            )
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
