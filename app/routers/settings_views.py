from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import get_current_user_id

router = APIRouter(prefix="/app/settings", tags=["settings"]) 
templates = Jinja2Templates(directory="app/templates")

# Simple currency options (code -> label)
CURRENCY_OPTIONS = [
    ("THB", "THB – Thai Baht (฿)"),
    ("USD", "USD – US Dollar ($)"),
    ("EUR", "EUR – Euro (€)"),
    ("GBP", "GBP – British Pound (£)"),
    ("JPY", "JPY – Japanese Yen (¥)"),
    ("AUD", "AUD – Australian Dollar (A$)"),
    ("SGD", "SGD – Singapore Dollar (S$)"),
]


def require_user(request: Request, db: Session) -> User | None:
    uid = get_current_user_id(request)
    if not uid:
        return None
    return db.query(User).get(uid)


@router.get("/", response_class=HTMLResponse)
def settings_index(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        "settings/index.html",
        {"request": request, "user": user, "currency_options": CURRENCY_OPTIONS, "msg": msg},
    )


@router.post("/")
def settings_update(request: Request, currency: str = Form(...), db: Session = Depends(get_db)):
    user = require_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    # Validate currency against whitelist
    codes = {c for c, _ in CURRENCY_OPTIONS}
    if currency not in codes:
        return templates.TemplateResponse(
            "settings/index.html",
            {"request": request, "user": user, "currency_options": CURRENCY_OPTIONS, "error": "Invalid currency selection."},
            status_code=400,
        )
    user.currency = currency
    db.commit()
    return RedirectResponse(url="/app/settings/?msg=Saved", status_code=303)
