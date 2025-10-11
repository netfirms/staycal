from typing import Optional
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, Response, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeSerializer(settings.SECRET_KEY, salt="staycal-session")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def set_session(response: Response, user_id: int):
    token = serializer.dumps({"uid": user_id})
    is_production = getattr(settings, "ENVIRONMENT", "development") == "production"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_production,
        path="/",
        max_age=settings.SESSION_MAX_AGE_DAYS * 24 * 60 * 60
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


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency to protect routes that require a logged-in user.
    Redirects to the login page if the user is not authenticated.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/auth/login"})
    
    user = db.query(User).get(user_id)
    if not user:
        # This case can happen if the user was deleted but the cookie remains.
        # We raise an exception that will also lead to a redirect.
        raise HTTPException(status_code=307, headers={"Location": "/auth/login"})
        
    return user
