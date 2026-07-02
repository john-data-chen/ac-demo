"""Projects router — CRUD scoped to board."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Board, Project, User

router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_ref(u: User | None) -> dict | None:
    if not u:
        return None
    return {"_id": str(u.id), "name": u.name, "email": u.email}


def _project_out(p: Project) -> dict:
    return {
        "_id": str(p.id),
        "title": p.title,
        "description": p.description,
        "owner": _user_ref(p.owner) or str(p.owner_id),
        "members": [_user_ref(m) for m in p.members],
        "board": str(p.board_id),
        "orderInBoard": p.order_in_board,
        "status": p.status,
        "dueDate": p.due_date.isoformat() if p.due_date else None,
        "assignee": _user_ref(p.assignee) if p.assignee else None,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


def _get_project_or_404(project_id: str, db: Session) -> Project:
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"statusCode": 404, "message": "Project not found", "error": "Not Found"},
        )
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"statusCode": 404, "message": "Project not found", "error": "Not Found"},
        )
    return project


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateProjectBody(BaseModel):
    title: str
    description: str | None = None
    boardId: str
    orderInBoard: int | None = None


class UpdateProjectBody(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    dueDate: str | None = None
    assigneeId: str | None = None
    orderInBoard: int | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_project(
    body: CreateProjectBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        board_id = uuid.UUID(body.boardId)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": f"Invalid board ID: {body.boardId}",
                "error": "Bad Request",
            },
        )

    board = db.get(Board, board_id)
    if not board:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": f"Invalid board ID: {body.boardId}",
                "error": "Bad Request",
            },
        )

    # Auto-assign orderInBoard if not provided
    if body.orderInBoard is None:
        max_order = (
            db.query(func.max(Project.order_in_board)).filter(Project.board_id == board_id).scalar()
        )
        order = (max_order or 0) + 1
    else:
        order = body.orderInBoard

    project = Project(
        title=body.title,
        description=body.description,
        owner_id=current_user.id,
        board_id=board_id,
        order_in_board=order,
        status="TODO",
        members=[current_user],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project)


@router.get("")
def get_by_board(boardId: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        bid = uuid.UUID(boardId)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"statusCode": 400, "message": "Invalid board ID", "error": "Bad Request"},
        )
    projects = (
        db.query(Project).filter(Project.board_id == bid).order_by(Project.order_in_board).all()
    )
    return [_project_out(p) for p in projects]


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    body: UpdateProjectBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    is_owner = project.owner_id == current_user.id

    # Permission: non-owner can only update orderInBoard
    if not is_owner:
        non_order_fields = {
            k for k, v in body.model_dump(exclude_unset=True).items() if k != "orderInBoard"
        }
        if non_order_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "statusCode": 400,
                    "message": "You do not have permission to update this project",
                    "error": "Bad Request",
                },
            )
        # Verify board membership for reorder
        board = db.get(Board, project.board_id)
        if not board or not any(m.id == current_user.id for m in board.members):
            raise HTTPException(
                status_code=400,
                detail={
                    "statusCode": 400,
                    "message": "You do not have permission to reorder projects in this board",
                    "error": "Bad Request",
                },
            )

    if body.title is not None:
        project.title = body.title
    if body.description is not None:
        project.description = body.description
    if body.status is not None:
        project.status = body.status
    if body.dueDate is not None:
        from datetime import datetime

        project.due_date = datetime.fromisoformat(body.dueDate)
    if body.orderInBoard is not None:
        project.order_in_board = body.orderInBoard
    if "assigneeId" in body.model_dump(exclude_unset=True):
        project.assignee_id = uuid.UUID(body.assigneeId) if body.assigneeId else None

    db.commit()
    db.refresh(project)
    return _project_out(project)


@router.delete("/{project_id}")
def delete_project(
    project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    project = _get_project_or_404(project_id, db)
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": "You do not have permission to delete this project",
                "error": "Bad Request",
            },
        )

    deleted_order = project.order_in_board
    board_id = project.board_id
    db.delete(project)
    db.flush()

    # Decrement orderInBoard for remaining projects
    remaining = (
        db.query(Project)
        .filter(Project.board_id == board_id, Project.order_in_board > deleted_order)
        .all()
    )
    for p in remaining:
        p.order_in_board -= 1

    db.commit()
    return {"message": "Project deleted successfully"}
