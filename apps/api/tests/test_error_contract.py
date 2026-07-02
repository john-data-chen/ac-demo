"""NestJS-compatible error contract: top-level {statusCode, message, error} bodies,
400 on nonexistent refs, status enum validation."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Board, Project, Task, User


@pytest.fixture
def board_and_project(test_engine, user_ids):
    _, id1, _, _ = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="EC Board", owner_id=u1.id, members=[u1])
        db.add(board)
        db.flush()
        project = Project(
            title="EC Project",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=0,
            status="TODO",
            members=[u1],
        )
        db.add(project)
        db.flush()
        task = Task(
            title="EC Task",
            status="TODO",
            board_id=board.id,
            project_id=project.id,
            creator_id=u1.id,
            last_modifier_id=u1.id,
            order_in_project=0,
        )
        db.add(task)
        db.commit()
        return str(board.id), str(project.id), str(task.id)


async def _login(c, email):
    return (await c.post("/auth/login", json={"email": email})).json()["access_token"]


@pytest.mark.asyncio
async def test_401_body_is_top_level_nest_shape(client):
    async with client as c:
        r = await c.get("/auth/profile")
    assert r.status_code == 401
    body = r.json()
    assert body["statusCode"] == 401
    assert body["message"] == "Unauthorized"
    assert body["error"] == "Unauthorized"
    assert "detail" not in body


@pytest.mark.asyncio
async def test_404_keeps_custom_message(client, user_ids):
    email1, _, _, _ = user_ids
    missing = uuid.uuid4()
    async with client as c:
        token = await _login(c, email1)
        r = await c.get(f"/boards/{missing}", headers={"Cookie": f"jwt={token}"})
    assert r.status_code == 404
    body = r.json()
    assert body["message"] == f'Board with ID "{missing}" not found'
    assert body["error"] == "Not Found"


@pytest.mark.asyncio
async def test_validation_error_is_400_nest_shape(client, user_ids):
    email1, _, _, _ = user_ids
    async with client as c:
        token = await _login(c, email1)
        r = await c.post("/boards", json={}, headers={"Cookie": f"jwt={token}"})
    assert r.status_code == 400
    body = r.json()
    assert body["statusCode"] == 400
    assert body["error"] == "Bad Request"
    assert isinstance(body["message"], list)


@pytest.mark.asyncio
async def test_create_task_nonexistent_project_is_400(client, user_ids, board_and_project):
    email1, _, _, _ = user_ids
    board_id, _, _ = board_and_project
    async with client as c:
        token = await _login(c, email1)
        r = await c.post(
            "/tasks",
            json={"title": "T", "board": board_id, "project": str(uuid.uuid4())},
            headers={"Cookie": f"jwt={token}"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_task_nonexistent_board_is_400(client, user_ids, board_and_project):
    email1, _, _, _ = user_ids
    _, project_id, _ = board_and_project
    async with client as c:
        token = await _login(c, email1)
        r = await c.post(
            "/tasks",
            json={"title": "T", "board": str(uuid.uuid4()), "project": project_id},
            headers={"Cookie": f"jwt={token}"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_move_task_nonexistent_project_is_400(client, user_ids, board_and_project):
    email1, _, _, _ = user_ids
    _, _, task_id = board_and_project
    async with client as c:
        token = await _login(c, email1)
        r = await c.patch(
            f"/tasks/{task_id}/move",
            json={"projectId": str(uuid.uuid4()), "orderInProject": 0},
            headers={"Cookie": f"jwt={token}"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_task_invalid_status_is_400(client, user_ids, board_and_project):
    email1, _, _, _ = user_ids
    _, _, task_id = board_and_project
    async with client as c:
        token = await _login(c, email1)
        r = await c.patch(
            f"/tasks/{task_id}",
            json={"status": "BOGUS"},
            headers={"Cookie": f"jwt={token}"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_project_invalid_status_is_400(client, user_ids, board_and_project):
    email1, _, _, _ = user_ids
    _, project_id, _ = board_and_project
    async with client as c:
        token = await _login(c, email1)
        r = await c.patch(
            f"/projects/{project_id}",
            json={"status": "BOGUS"},
            headers={"Cookie": f"jwt={token}"},
        )
    assert r.status_code == 400
