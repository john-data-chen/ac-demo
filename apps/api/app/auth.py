"""JWT auth utilities — mirrors NestJS passport-jwt + cookie behavior."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

_bearer = HTTPBearer(auto_error=False)


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"statusCode": 401, "message": "Token expired", "error": "Unauthorized"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"statusCode": 401, "message": "Invalid token", "error": "Unauthorized"},
        )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    jwt_cookie: str | None = Cookie(default=None, alias="jwt"),
    db: Session = Depends(get_db),
) -> User:
    """Extract JWT from cookie first, then Authorization header (mirrors JwtStrategy)."""
    token: str | None = None

    if jwt_cookie:
        token = jwt_cookie
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"statusCode": 401, "message": "Unauthorized", "error": "Unauthorized"},
        )

    payload = _decode_token(token)
    email = payload.get("email")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"statusCode": 401, "message": "User not found", "error": "Unauthorized"},
        )
    return user
