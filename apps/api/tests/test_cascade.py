"""Cascade delete test: Board → Project → Task"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Board, Project, Task, User

TEST_DB_URL = "postgresql+psycopg://root:123456@localhost:5432/task_manager"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


def test_cascade_board_delete(db):
    user = User(email=f"cascade_{uuid.uuid4()}@test.com", name="Cascade Test")
    db.add(user)
    db.flush()

    board = Board(title="Board", owner_id=user.id, members=[user])
    db.add(board)
    db.flush()

    project = Project(
        title="Project",
        owner_id=user.id,
        board_id=board.id,
        status="TODO",
        order_in_board=0,
        members=[user],
    )
    db.add(project)
    db.flush()

    task = Task(
        title="Task",
        status="TODO",
        board_id=board.id,
        project_id=project.id,
        creator_id=user.id,
        last_modifier_id=user.id,
        order_in_project=0,
    )
    db.add(task)
    db.commit()

    task_id = task.id
    project_id = project.id
    board_id = board.id

    # Delete board — should cascade to project and task
    db.delete(board)
    db.commit()

    assert db.get(Board, board_id) is None
    assert db.get(Project, project_id) is None
    assert db.get(Task, task_id) is None
