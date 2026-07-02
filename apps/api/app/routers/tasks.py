"""Tasks router — CRUD + move."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Board, Project, Task, User
from app.serializers import user_ref as _user_ref

TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE"]

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_out(t: Task) -> dict:
    out: dict = {
        "_id": str(t.id),
        "title": t.title,
        "status": t.status,
        "board": str(t.board_id),
        "project": str(t.project_id),
        "creator": _user_ref(t.creator),
        "lastModifier": _user_ref(t.last_modifier) or _user_ref(t.creator),
        "assignee": _user_ref(t.assignee),
        "orderInProject": t.order_in_project,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
    }
    if t.description:
        out["description"] = t.description
    if t.due_date:
        out["dueDate"] = t.due_date.isoformat()
    return out


def _get_task_or_404(task_id: str, db: Session) -> Task:
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f"Task with ID {task_id} not found",
                "error": "Not Found",
            },
        )
    task = db.get(Task, tid)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "statusCode": 404,
                "message": f"Task with ID {task_id} not found",
                "error": "Not Found",
            },
        )
    return task


def _check_task_permission(task: Task, current_user: User, require_creator: bool = False):
    is_creator = task.creator_id == current_user.id
    is_assignee = task.assignee_id == current_user.id
    if require_creator and not is_creator:
        raise HTTPException(
            status_code=403,
            detail={
                "statusCode": 403,
                "message": "Only the task creator can perform this action",
                "error": "Forbidden",
            },
        )
    if not is_creator and not is_assignee:
        raise HTTPException(
            status_code=403,
            detail={
                "statusCode": 403,
                "message": "You do not have permission to modify this task",
                "error": "Forbidden",
            },
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateTaskBody(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus | None = "TODO"
    dueDate: str | None = None
    orderInProject: int | None = 0
    board: str
    project: str
    assignee: str | None = None


class UpdateTaskBody(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    dueDate: str | None = None
    assigneeId: str | None = None
    lastModifier: str | None = None
    orderInProject: int | None = None


class MoveTaskBody(BaseModel):
    projectId: str
    orderInProject: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_task(
    body: CreateTaskBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project_id = uuid.UUID(body.project)
        board_id = uuid.UUID(body.board)
        assignee_id = uuid.UUID(body.assignee) if body.assignee else None
        due_date = datetime.fromisoformat(body.dueDate) if body.dueDate else None
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": "Invalid ID or date format",
                "error": "Bad Request",
            },
        )

    # Referenced rows must exist, otherwise commit dies with an FK IntegrityError (500)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": f"Invalid project ID: {body.project}",
                "error": "Bad Request",
            },
        )
    if not db.get(Board, board_id):
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": f"Invalid board ID: {body.board}",
                "error": "Bad Request",
            },
        )

    task = Task(
        title=body.title,
        description=body.description,
        status=body.status or "TODO",
        due_date=due_date,
        order_in_project=body.orderInProject or 0,
        board_id=board_id,
        project_id=project_id,
        creator_id=current_user.id,
        last_modifier_id=current_user.id,
        assignee_id=assignee_id,
    )
    db.add(task)

    # Add creator to project members if not already
    if not any(m.id == current_user.id for m in project.members):
        project.members.append(current_user)

    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.get("")
def find_all(
    projectId: str | None = None,
    assigneeId: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Task)
    if projectId:
        try:
            q = q.filter(Task.project_id == uuid.UUID(projectId))
        except ValueError:
            pass
    if assigneeId:
        try:
            q = q.filter(Task.assignee_id == uuid.UUID(assigneeId))
        except ValueError:
            pass
    tasks = q.all()
    return [_task_out(t) for t in tasks]


@router.get("/{task_id}")
def find_one(task_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = _get_task_or_404(task_id, db)
    return _task_out(task)


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    body: UpdateTaskBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db)
    _check_task_permission(task, current_user)

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.status is not None:
        task.status = body.status
    try:
        if body.dueDate is not None:
            task.due_date = datetime.fromisoformat(body.dueDate) if body.dueDate else None
        if body.orderInProject is not None:
            task.order_in_project = body.orderInProject
        if "assigneeId" in body.model_dump(exclude_unset=True):
            task.assignee_id = uuid.UUID(body.assigneeId) if body.assigneeId else None
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": "Invalid ID or date format",
                "error": "Bad Request",
            },
        )
    task.last_modifier_id = current_user.id

    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.delete("/{task_id}", status_code=200)
def delete_task(
    task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    task = _get_task_or_404(task_id, db)
    _check_task_permission(task, current_user, require_creator=True)

    deleted_order = task.order_in_project
    project_id = task.project_id
    db.delete(task)
    db.flush()

    # Decrement orderInProject for remaining tasks
    remaining = (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.order_in_project > deleted_order)
        .all()
    )
    for t in remaining:
        t.order_in_project -= 1

    db.commit()
    return {}


@router.patch("/{task_id}/move")
def move_task(
    task_id: str,
    body: MoveTaskBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db)
    _check_task_permission(task, current_user)

    try:
        new_project_id = uuid.UUID(body.projectId)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"statusCode": 400, "message": "Invalid project ID", "error": "Bad Request"},
        )

    if not db.get(Project, new_project_id):
        raise HTTPException(
            status_code=400,
            detail={"statusCode": 400, "message": "Invalid project ID", "error": "Bad Request"},
        )

    old_project_id = task.project_id
    old_order = task.order_in_project
    new_order = body.orderInProject

    task.project_id = new_project_id
    task.order_in_project = new_order
    task.last_modifier_id = current_user.id

    if old_project_id == new_project_id:
        # Reorder within same project
        if old_order < new_order:
            others = (
                db.query(Task)
                .filter(
                    Task.project_id == new_project_id,
                    Task.order_in_project > old_order,
                    Task.order_in_project <= new_order,
                    Task.id != task.id,
                )
                .all()
            )
            for t in others:
                t.order_in_project -= 1
        elif old_order > new_order:
            others = (
                db.query(Task)
                .filter(
                    Task.project_id == new_project_id,
                    Task.order_in_project >= new_order,
                    Task.order_in_project < old_order,
                    Task.id != task.id,
                )
                .all()
            )
            for t in others:
                t.order_in_project += 1
    else:
        # Different project: decrement old, increment new
        old_remaining = (
            db.query(Task)
            .filter(Task.project_id == old_project_id, Task.order_in_project > old_order)
            .all()
        )
        for t in old_remaining:
            t.order_in_project -= 1
        new_shifted = (
            db.query(Task)
            .filter(
                Task.project_id == new_project_id,
                Task.order_in_project >= new_order,
                Task.id != task.id,
            )
            .all()
        )
        for t in new_shifted:
            t.order_in_project += 1

    db.commit()
    db.refresh(task)
    return _task_out(task)
