"""Users router — GET /users, GET /users/search"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])


def _user_out(u: User) -> dict:
    return {
        "_id": str(u.id),
        "email": u.email,
        "name": u.name,
        "createdAt": u.created_at.isoformat() if u.created_at else None,
        "updatedAt": u.updated_at.isoformat() if u.updated_at else None,
    }


@router.get("")
def find_all(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    users = db.query(User).all()
    return {"users": [_user_out(u) for u in users]}


@router.get("/search")
def search(username: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    users = db.query(User).filter(User.name.ilike(f"%{username}%")).all()
    return {"users": [_user_out(u) for u in users]}
