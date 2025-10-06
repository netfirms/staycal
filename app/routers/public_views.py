from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    from ..config import settings
    pricing = {
        "basic_monthly": getattr(settings, "PLAN_BASIC_MONTHLY", 249),
        "basic_yearly": getattr(settings, "PLAN_BASIC_YEARLY", 2490),
        "pro_monthly": getattr(settings, "PLAN_PRO_MONTHLY", 699),
        "pro_yearly": getattr(settings, "PLAN_PRO_YEARLY", 6990),
    }
    return templates.TemplateResponse("landing.html", {"request": request, "pricing": pricing})
