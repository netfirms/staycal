from typing import Optional
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, Response
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeSerializer(settings.SECRET_KEY, salt="staycal-session")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def set_session(response: Response, user_id: int):
    token = serializer.dumps({"uid": user_id})
    # Use getattr for resilience, defaulting to 'development' if the setting is missing.
    is_production = getattr(settings, "ENVIRONMENT", "development") == "production"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_production,
        path="/",
    )


def clear_session(response: Response):
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")


def get_current_user_id(request: Request) -> Optional[int]:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        data = serializer.loads(token)
        return int(data.get("uid"))
    except (BadSignature, ValueError, TypeError):
        return None
