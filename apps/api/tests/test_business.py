"""Business router tests: boards, projects, tasks happy path + key error paths."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.main import app
from app.models import Board, Project, Task, User

TEST_DB_URL = "postgresql+psycopg://root:123456@localhost:5432/task_manager"


@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng


@pytest.fixture(scope="module")
def user_ids(test_engine):
    """Create two users, return their (email1, id1, email2, id2)."""
    with Session(test_engine) as db:
        u1 = User(email=f"biz1_{uuid.uuid4()}@test.com", name="User One")
        u2 = User(email=f"biz2_{uuid.uuid4()}@test.com", name="User Two")
        db.add_all([u1, u2])
        db.commit()
        return (u1.email, str(u1.id), u2.email, str(u2.id))


@pytest.fixture
def client(test_engine):
    def override_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ============================================================
# BOARDS
# ============================================================


@pytest.mark.asyncio
async def test_create_board(client, user_ids):
    email1, id1, _, _ = user_ids
    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        r = await c.post("/boards", json={"title": "Test Board"}, cookies={"jwt": token})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test Board"
    assert any(m["_id"] == id1 for m in data["members"])


@pytest.mark.asyncio
async def test_get_boards(client, user_ids):
    email1, _, _, _ = user_ids
    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        r = await c.get("/boards", cookies={"jwt": token})
    assert r.status_code == 200
    data = r.json()
    assert "myBoards" in data
    assert "teamBoards" in data


@pytest.mark.asyncio
async def test_delete_board_not_owner(client, user_ids, test_engine):
    email1, id1, email2, _ = user_ids
    # Create board as u1 using IDs only
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="To Delete", owner_id=u1.id, members=[u1])
        db.add(board)
        db.commit()
        board_id = str(board.id)

    async with client as c:
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]
        r = await c.delete(f"/boards/{board_id}", cookies={"jwt": token2})
    assert r.status_code == 404


# ============================================================
# PROJECTS
# ============================================================


@pytest.mark.asyncio
async def test_create_project(client, user_ids, test_engine):
    email1, id1, _, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="Board for Projects", owner_id=u1.id, members=[u1])
        db.add(board)
        db.commit()
        board_id = str(board.id)

    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        r = await c.post(
            "/projects", json={"title": "Project A", "boardId": board_id}, cookies={"jwt": token}
        )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Project A"
    assert data["board"] == board_id


@pytest.mark.asyncio
async def test_get_projects_by_board(client, user_ids, test_engine):
    email1, id1, _, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="Board for List", owner_id=u1.id, members=[u1])
        db.add(board)
        db.commit()
        board_id = str(board.id)

    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        await c.post("/projects", json={"title": "P1", "boardId": board_id}, cookies={"jwt": token})
        r = await c.get(f"/projects?boardId={board_id}", cookies={"jwt": token})
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_delete_project_non_owner(client, user_ids, test_engine):
    email1, id1, email2, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="B", owner_id=u1.id, members=[u1])
        db.add(board)
        db.flush()
        project = Project(
            title="P",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=0,
            status="TODO",
            members=[u1],
        )
        db.add(project)
        db.commit()
        project_id = str(project.id)

    async with client as c:
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]
        r = await c.delete(f"/projects/{project_id}", cookies={"jwt": token2})
    assert r.status_code == 400


# ============================================================
# TASKS
# ============================================================


@pytest.mark.asyncio
async def test_create_and_get_task(client, user_ids, test_engine):
    email1, id1, _, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="TB", owner_id=u1.id, members=[u1])
        db.add(board)
        db.flush()
        project = Project(
            title="TP",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=0,
            status="TODO",
            members=[u1],
        )
        db.add(project)
        db.commit()
        board_id = str(board.id)
        project_id = str(project.id)

    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        r_create = await c.post(
            "/tasks",
            json={"title": "My Task", "board": board_id, "project": project_id},
            cookies={"jwt": token},
        )
        assert r_create.status_code == 201
        task_id = r_create.json()["_id"]

        r_get = await c.get(f"/tasks/{task_id}", cookies={"jwt": token})
        assert r_get.status_code == 200
        assert r_get.json()["title"] == "My Task"


@pytest.mark.asyncio
async def test_delete_task_non_creator(client, user_ids, test_engine):
    email1, id1, email2, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="TB2", owner_id=u1.id, members=[u1])
        db.add(board)
        db.flush()
        project = Project(
            title="TP2",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=0,
            status="TODO",
            members=[u1],
        )
        db.add(project)
        db.flush()
        task = Task(
            title="T",
            status="TODO",
            board_id=board.id,
            project_id=project.id,
            creator_id=u1.id,
            last_modifier_id=u1.id,
            order_in_project=0,
        )
        db.add(task)
        db.commit()
        task_id = str(task.id)

    async with client as c:
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]
        r = await c.delete(f"/tasks/{task_id}", cookies={"jwt": token2})
    assert r.status_code == 403
