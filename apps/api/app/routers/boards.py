"""Boards router — full CRUD + member management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Board, User

router = APIRouter(prefix="/boards", tags=["boards"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _board_out(b: Board) -> dict:
    return {
        "_id": str(b.id),
        "title": b.title,
        "description": b.description,
        "owner": str(b.owner_id),
        "members": [str(m.id) for m in b.members],
        "projects": [str(p.id) for p in b.projects],
        "createdAt": b.created_at.isoformat() if b.created_at else None,
        "updatedAt": b.updated_at.isoformat() if b.updated_at else None,
    }


def _get_board_or_404(board_id: str, db: Session) -> Board:
    try:
        bid = uuid.UUID(board_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f'Board with ID "{board_id}" not found',
                "error": "Not Found",
            },
        )
    board = db.get(Board, bid)
    if not board:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f'Board with ID "{board_id}" not found',
                "error": "Not Found",
            },
        )
    return board


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateBoardBody(BaseModel):
    title: str
    description: str | None = None
    members: list[str] | None = None
    projects: list[str] | None = None


class UpdateBoardBody(BaseModel):
    title: str | None = None
    description: str | None = None
    members: list[str] | None = None
    projects: list[str] | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_board(
    body: CreateBoardBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = Board(title=body.title, description=body.description, owner_id=current_user.id)
    # Owner always in members
    member_ids = set([str(current_user.id)] + (body.members or []))
    members = db.query(User).filter(User.id.in_([uuid.UUID(mid) for mid in member_ids])).all()
    board.members = members
    db.add(board)
    db.commit()
    db.refresh(board)
    return _board_out(board)


@router.get("")
def find_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    my_boards = db.query(Board).filter(Board.owner_id == current_user.id).all()
    team_boards = (
        db.query(Board)
        .filter(Board.owner_id != current_user.id)
        .filter(Board.members.any(User.id == current_user.id))
        .all()
    )
    return {
        "myBoards": [_board_out(b) for b in my_boards],
        "teamBoards": [_board_out(b) for b in team_boards],
    }


@router.get("/{board_id}")
def find_one(
    board_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    board = _get_board_or_404(board_id, db)
    is_owner = board.owner_id == current_user.id
    is_member = any(m.id == current_user.id for m in board.members)
    if not is_owner and not is_member:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f'Board with ID "{board_id}" not found',
                "error": "Not Found",
            },
        )
    return _board_out(board)


@router.patch("/{board_id}")
def update_board(
    board_id: str,
    body: UpdateBoardBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = _get_board_or_404(board_id, db)
    is_owner = board.owner_id == current_user.id
    is_member = any(m.id == current_user.id for m in board.members)
    if not is_owner and not is_member:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f'Board with ID "{board_id}" not found or access denied',
                "error": "Not Found",
            },
        )
    if body.title is not None:
        board.title = body.title
    if body.description is not None:
        board.description = body.description
    if body.members is not None:
        board.members = (
            db.query(User).filter(User.id.in_([uuid.UUID(mid) for mid in body.members])).all()
        )
    db.commit()
    db.refresh(board)
    return _board_out(board)


@router.delete("/{board_id}")
def delete_board(
    board_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    board = _get_board_or_404(board_id, db)
    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f'Board with ID "{board_id}" not found',
                "error": "Not Found",
            },
        )
    db.delete(board)
    db.commit()
    return {"message": "Board deleted successfully"}


@router.post("/{board_id}/members/{member_id}")
def add_member(
    board_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = _get_board_or_404(board_id, db)
    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={"statusCode": 403, "message": "Forbidden", "error": "Forbidden"},
        )
    try:
        uid = uuid.UUID(member_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"statusCode": 404, "message": "User not found", "error": "Not Found"},
        )
    user = db.get(User, uid)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"statusCode": 404, "message": "User not found", "error": "Not Found"},
        )
    if not any(m.id == user.id for m in board.members):
        board.members.append(user)
        db.commit()
        db.refresh(board)
    return _board_out(board)


@router.delete("/{board_id}/members/{member_id}")
def remove_member(
    board_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = _get_board_or_404(board_id, db)
    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={"statusCode": 403, "message": "Forbidden", "error": "Forbidden"},
        )
    try:
        uid = uuid.UUID(member_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"statusCode": 404, "message": "User not found", "error": "Not Found"},
        )
    board.members = [m for m in board.members if m.id != uid]
    db.commit()
    db.refresh(board)
    return _board_out(board)
