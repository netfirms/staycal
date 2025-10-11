from fastapi import APIRouter, Request
from ..templating import templates

router = APIRouter(prefix="/ui", tags=["ui"])

@router.get("/image-modal")
def image_modal(request: Request, image_url: str, alt_text: str = ""):
    return templates.TemplateResponse(
        "partials/image_modal.html",
        {
            "request": request,
            "image_url": image_url,
            "alt_text": alt_text,
        },
    )
