import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models import Board, Project, User


@pytest.mark.asyncio
async def test_board_not_found(client, user_ids):
    email1, _, _, _ = user_ids
    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        r1 = await c.get(f"/boards/{uuid.uuid4()}", headers={"Cookie": f"jwt={token}"})
        assert r1.status_code == 404
        r2 = await c.get("/boards/invalid-uuid", headers={"Cookie": f"jwt={token}"})
        assert r2.status_code == 404


@pytest.mark.asyncio
async def test_board_update_access_and_fields(client, user_ids, test_engine):
    email1, id1, email2, id2 = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="B", owner_id=u1.id, members=[u1])
        db.add(board)
        db.commit()
        board_id = str(board.id)
    async with client as c:
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]
        # Update as non-member
        r1 = await c.patch(
            f"/boards/{board_id}", json={"title": "T"}, headers={"Cookie": f"jwt={token2}"}
        )
        assert r1.status_code == 404

        token1 = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        # Update fields
        r2 = await c.patch(
            f"/boards/{board_id}",
            json={"title": "New", "description": "D", "members": [id1, id2]},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r2.status_code == 200
        assert r2.json()["title"] == "New"
        assert r2.json()["description"] == "D"
        assert len(r2.json()["members"]) == 2


@pytest.mark.asyncio
async def test_board_members(client, user_ids, test_engine):
    email1, id1, email2, id2 = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        board = Board(title="B2", owner_id=u1.id, members=[u1])
        db.add(board)
        db.commit()
        board_id = str(board.id)
    async with client as c:
        token1 = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]

        # Add member 404 (user not found)
        r_add_fail = await c.post(
            f"/boards/{board_id}/members/{uuid.uuid4()}", headers={"Cookie": f"jwt={token1}"}
        )
        assert r_add_fail.status_code == 404

        # Add member 404 (invalid user uuid)
        r_add_fail2 = await c.post(
            f"/boards/{board_id}/members/invalid", headers={"Cookie": f"jwt={token1}"}
        )
        assert r_add_fail2.status_code == 404

        # Add member 403 (non-owner)
        r_add_fail3 = await c.post(
            f"/boards/{board_id}/members/{id2}", headers={"Cookie": f"jwt={token2}"}
        )
        assert r_add_fail3.status_code == 403

        # Add member success
        r_add = await c.post(
            f"/boards/{board_id}/members/{id2}", headers={"Cookie": f"jwt={token1}"}
        )
        assert r_add.status_code == 200

        # Remove member 404 invalid uuid
        r_rem_fail = await c.delete(
            f"/boards/{board_id}/members/invalid", headers={"Cookie": f"jwt={token1}"}
        )
        assert r_rem_fail.status_code == 404

        # Remove member 403 non-owner
        r_rem_fail2 = await c.delete(
            f"/boards/{board_id}/members/{id2}", headers={"Cookie": f"jwt={token2}"}
        )
        assert r_rem_fail2.status_code == 403

        # Remove member success
        r_rem = await c.delete(
            f"/boards/{board_id}/members/{id2}", headers={"Cookie": f"jwt={token1}"}
        )
        assert r_rem.status_code == 200


@pytest.mark.asyncio
async def test_project_errors(client, user_ids, test_engine):
    email1, id1, email2, id2 = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        u2 = db.get(User, uuid.UUID(id2))
        board = Board(title="B", owner_id=u1.id, members=[u1, u2])
        db.add(board)
        db.commit()
        board_id = str(board.id)

    async with client as c:
        token1 = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]

        # invalid board id in create
        r = await c.post(
            "/projects",
            json={"title": "P", "boardId": "invalid"},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 400

        # board not found in create
        r = await c.post(
            "/projects",
            json={"title": "P", "boardId": str(uuid.uuid4())},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 400

        # create with orderInBoard
        r = await c.post(
            "/projects",
            json={"title": "P1", "boardId": board_id, "orderInBoard": 5},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 201
        p1_id = r.json()["_id"]

        r = await c.post(
            "/projects",
            json={"title": "P2", "boardId": board_id},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 201

        # get projects by board invalid id
        r = await c.get("/projects?boardId=invalid", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 400

        # update project non-owner tries to update title
        r = await c.patch(
            f"/projects/{p1_id}", json={"title": "X"}, headers={"Cookie": f"jwt={token2}"}
        )
        assert r.status_code == 400

        # update project valid fields
        r = await c.patch(
            f"/projects/{p1_id}",
            json={
                "title": "T",
                "description": "D",
                "status": "DONE",
                "dueDate": datetime.now().isoformat(),
                "orderInBoard": 10,
                "assigneeId": id2,
            },
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 200

        # project not found
        r = await c.patch(
            f"/projects/{uuid.uuid4()}", json={"title": "T"}, headers={"Cookie": f"jwt={token1}"}
        )
        assert r.status_code == 404
        r = await c.patch(
            "/projects/invalid", json={"title": "T"}, headers={"Cookie": f"jwt={token1}"}
        )
        assert r.status_code == 404

        # delete project
        r = await c.delete(f"/projects/{p1_id}", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_task_errors_and_moves(client, user_ids, test_engine):
    email1, id1, email2, id2 = user_ids
    with Session(test_engine) as db:
        u1 = db.get(User, uuid.UUID(id1))
        u2 = db.get(User, uuid.UUID(id2))
        board = Board(title="B", owner_id=u1.id, members=[u1, u2])
        db.add(board)
        db.flush()
        p1 = Project(
            title="P1",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=0,
            status="TODO",
            members=[u1],
        )
        p2 = Project(
            title="P2",
            owner_id=u1.id,
            board_id=board.id,
            order_in_board=1,
            status="TODO",
            members=[u1],
        )
        db.add_all([p1, p2])
        db.commit()
        board_id = str(board.id)
        p1_id = str(p1.id)
        p2_id = str(p2.id)

    async with client as c:
        token1 = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]
        token2 = (await c.post("/auth/login", json={"email": email2})).json()["access_token"]

        # create tasks
        r = await c.post(
            "/tasks",
            json={"title": "T1", "board": board_id, "project": p1_id},
            headers={"Cookie": f"jwt={token1}"},
        )
        t1 = r.json()["_id"]
        r = await c.post(
            "/tasks",
            json={"title": "T2", "board": board_id, "project": p1_id},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 201
        r = await c.post(
            "/tasks",
            json={"title": "T3", "board": board_id, "project": p2_id},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 201

        # invalid create
        r = await c.post(
            "/tasks",
            json={"title": "T", "board": "inv", "project": "inv"},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 400

        # update task forbidden
        r = await c.patch(f"/tasks/{t1}", json={"title": "X"}, headers={"Cookie": f"jwt={token2}"})
        assert r.status_code == 403

        # update task valid fields
        r = await c.patch(
            f"/tasks/{t1}",
            json={
                "title": "New T1",
                "description": "D",
                "status": "DONE",
                "dueDate": datetime.now().isoformat(),
                "orderInProject": 2,
                "assigneeId": id1,
            },
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 200

        # find tasks query
        r = await c.get(
            f"/tasks?projectId={p1_id}&assigneeId={id1}", headers={"Cookie": f"jwt={token1}"}
        )
        assert r.status_code == 200

        # find tasks query invalid
        r = await c.get("/tasks?projectId=inv&assigneeId=inv", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 200

        # move task within same project down
        r = await c.patch(
            f"/tasks/{t1}/move",
            json={"projectId": p1_id, "orderInProject": 10},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 200

        # move task within same project up
        r = await c.patch(
            f"/tasks/{t1}/move",
            json={"projectId": p1_id, "orderInProject": 0},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 200

        # move task to different project
        r = await c.patch(
            f"/tasks/{t1}/move",
            json={"projectId": p2_id, "orderInProject": 0},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 200

        # invalid move project id
        r = await c.patch(
            f"/tasks/{t1}/move",
            json={"projectId": "invalid", "orderInProject": 0},
            headers={"Cookie": f"jwt={token1}"},
        )
        assert r.status_code == 400

        # task not found
        r = await c.get(f"/tasks/{uuid.uuid4()}", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 404
        r = await c.get("/tasks/invalid", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 404

        # delete task
        r = await c.delete(f"/tasks/{t1}", headers={"Cookie": f"jwt={token1}"})
        assert r.status_code == 200
