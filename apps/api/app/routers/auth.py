"""Auth router — /auth/login, /auth/profile, /auth/logout"""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import JWT_EXPIRE_DAYS, create_token, get_current_user
from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE = JWT_EXPIRE_DAYS * 24 * 60 * 60  # seconds


def _is_secure() -> bool:
    return settings.node_env == "production"


def _set_auth_cookies(response: Response, token: str) -> None:
    secure = _is_secure()
    response.set_cookie(
        key="jwt",
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )
    response.set_cookie(
        key="isAuthenticated",
        value="true",
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    secure = _is_secure()
    response.set_cookie(
        key="jwt", value="", httponly=True, secure=secure, samesite="lax", max_age=0, path="/"
    )
    response.set_cookie(
        key="isAuthenticated",
        value="",
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=0,
        path="/",
    )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginBody(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user: User | None = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "statusCode": 401,
                "message": "The login email is incorrect, please correct it",
                "error": "Unauthorized",
            },
        )

    token = create_token(str(user.id), user.email)
    _set_auth_cookies(response, token)

    return {
        "user": {"_id": str(user.id), "email": user.email, "name": user.name},
        "access_token": token,
    }


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {"_id": str(current_user.id), "email": current_user.email}


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out"}
