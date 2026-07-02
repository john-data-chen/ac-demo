"""
Seed script — migrates demo data from NestJS demoData.ts constants.

Usage:
  uv run python -m app.seed           # skip if data exists
  uv run python -m app.seed --force   # drop and re-seed
"""

import sys

from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import Board, Project, Task, User

# ---------------------------------------------------------------------------
# Demo data (migrated from apps/api/src/constants/demoData.ts)
# ---------------------------------------------------------------------------

DEMO_USERS = [
    {"email": "john.doe@example.com", "name": "John Doe"},
    {"email": "jane.doe@example.com", "name": "Jane Doe"},
    {"email": "mark.s@example.com", "name": "Mark S"},
]

DEMO_BOARDS = [
    {"title": "Mark's Kanban", "description": "My personal tasks and projects", "owner_index": 2},
    {"title": "John's Kanban", "description": "My personal tasks and projects", "owner_index": 0},
    {"title": "Jane's Kanban", "description": "My personal tasks and projects", "owner_index": 1},
    {"title": "Dev Team Board", "description": "public board for Dev Team", "owner_index": 0},
]

DEMO_PROJECTS = [
    {"title": "Mark's todo list", "description": "This is demo project 1", "board_index": 0},
    {"title": "Demo Project 2", "description": "This is demo project 2", "board_index": 3},
    {"title": "Demo Project 3", "description": "This is demo project 3", "board_index": 3},
]

DEMO_TASKS = [
    {
        "title": "Task 1",
        "description": "This is my first task",
        "status": "TODO",
        "project_index": 0,
    },
    {
        "title": "Task 2",
        "description": "This is task 2",
        "status": "IN_PROGRESS",
        "project_index": 0,
    },
    {"title": "Task 3", "description": "This is task 3", "status": "DONE", "project_index": 1},
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


def seed(force: bool = False):
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        existing = db.query(User).filter(User.email == DEMO_USERS[0]["email"]).first()
        if existing and not force:
            print("Demo data already exists. Use --force to re-seed.")
            return

        if force and existing:
            print("Dropping existing demo data...")
            # Delete in FK order
            demo_emails = {u["email"] for u in DEMO_USERS}
            users = db.query(User).filter(User.email.in_(demo_emails)).all()
            for u in users:
                db.delete(u)
            db.commit()

        print("Seeding demo users...")
        users = []
        for data in DEMO_USERS:
            u = User(email=data["email"], name=data["name"])
            db.add(u)
            users.append(u)
        db.flush()

        print("Seeding demo boards...")
        boards = []
        for data in DEMO_BOARDS:
            owner = users[data["owner_index"]]
            b = Board(
                title=data["title"],
                description=data["description"],
                owner_id=owner.id,
                members=[owner],
            )
            db.add(b)
            boards.append(b)
        db.flush()

        print("Seeding demo projects...")
        projects = []
        for i, data in enumerate(DEMO_PROJECTS):
            board = boards[data["board_index"]]
            owner = board.owner
            p = Project(
                title=data["title"],
                description=data["description"],
                owner_id=owner.id,
                board_id=board.id,
                order_in_board=i,
                status="TODO",
                members=[owner],
            )
            db.add(p)
            projects.append(p)
        db.flush()

        print("Seeding demo tasks...")
        for i, data in enumerate(DEMO_TASKS):
            project = projects[data["project_index"]]
            owner_id = project.owner_id
            t = Task(
                title=data["title"],
                description=data["description"],
                status=data["status"],
                order_in_project=i,
                board_id=project.board_id,
                project_id=project.id,
                creator_id=owner_id,
                last_modifier_id=owner_id,
            )
            db.add(t)

        db.commit()
        print("Done! Demo data seeded successfully.")
        print(f"  Users: {len(DEMO_USERS)}")
        print(f"  Boards: {len(DEMO_BOARDS)}")
        print(f"  Projects: {len(DEMO_PROJECTS)}")
        print(f"  Tasks: {len(DEMO_TASKS)}")
        print()
        print("Login with any of these emails (no password required):")
        for u in DEMO_USERS:
            print(f"  {u['email']}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    seed(force=force)
