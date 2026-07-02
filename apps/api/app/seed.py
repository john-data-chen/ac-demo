"""
Seed script — migrates demo data from NestJS demoData.ts constants.

Usage:
  uv run python -m app.seed           # skip if data exists
  uv run python -m app.seed --force   # drop and re-seed
"""

import sys
from datetime import UTC, datetime, timedelta

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
    {"title": "Mark's Kanban", "description": "My personal tasks and projects"},
    {"title": "John's Kanban", "description": "My personal tasks and projects"},
    {"title": "Jane's Kanban", "description": "My personal tasks and projects"},
    {"title": "Dev Team Board", "description": "public board for Dev Team"},
]

DEMO_PROJECTS = [
    {"title": "Mark's todo list", "description": "This is demo project 1"},
    {"title": "Demo Project 2", "description": "This is demo project 2"},
    {"title": "Demo Project 3", "description": "This is demo project 3"},
]

DEMO_TASKS = [
    {"title": "Task 1", "description": "This is my first task", "status": "TODO"},
    {"title": "Task 2", "description": "This is task 2", "status": "IN_PROGRESS"},
    {"title": "Task 3", "description": "This is task 3", "status": "DONE"},
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
            # owner_id has no ON DELETE CASCADE, so drop tasks, then boards, then users.
            demo_emails = {u["email"] for u in DEMO_USERS}
            users = db.query(User).filter(User.email.in_(demo_emails)).all()
            user_ids = [u.id for u in users]

            boards = db.query(Board).filter(Board.owner_id.in_(user_ids)).all()
            board_ids = [b.id for b in boards]

            if board_ids:
                tasks = db.query(Task).filter(Task.board_id.in_(board_ids)).all()
                for t in tasks:
                    db.delete(t)
                db.flush()

            for b in boards:
                db.delete(b)
            db.flush()
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
        boards = [
            Board(
                title=DEMO_BOARDS[0]["title"],
                description=DEMO_BOARDS[0]["description"],
                owner_id=users[2].id,
                members=[users[2]],
            ),
            Board(
                title=DEMO_BOARDS[1]["title"],
                description=DEMO_BOARDS[1]["description"],
                owner_id=users[0].id,
                members=[users[0]],
            ),
            Board(
                title=DEMO_BOARDS[2]["title"],
                description=DEMO_BOARDS[2]["description"],
                owner_id=users[1].id,
                members=[users[1]],
            ),
            Board(
                title=DEMO_BOARDS[3]["title"],
                description=DEMO_BOARDS[3]["description"],
                owner_id=users[1].id,
                members=[users[0], users[1], users[2]],
            ),
        ]
        db.add_all(boards)
        db.flush()

        print("Seeding demo projects...")
        projects = [
            Project(
                title=DEMO_PROJECTS[0]["title"],
                description=DEMO_PROJECTS[0]["description"],
                owner_id=users[2].id,
                board_id=boards[0].id,
                order_in_board=0,
                status="TODO",
                members=[users[2]],
            ),
            Project(
                title=DEMO_PROJECTS[1]["title"],
                description=DEMO_PROJECTS[1]["description"],
                owner_id=users[0].id,
                board_id=boards[3].id,
                order_in_board=0,
                status="TODO",
                members=[users[0], users[2]],
            ),
            Project(
                title=DEMO_PROJECTS[2]["title"],
                description=DEMO_PROJECTS[2]["description"],
                owner_id=users[1].id,
                board_id=boards[3].id,
                order_in_board=1,
                status="TODO",
                members=[users[1], users[2]],
            ),
        ]
        db.add_all(projects)
        db.flush()

        print("Seeding demo tasks...")
        now = datetime.now(UTC)
        tasks = [
            Task(
                title=DEMO_TASKS[0]["title"],
                description=DEMO_TASKS[0]["description"],
                status=DEMO_TASKS[0]["status"],
                order_in_project=0,
                board_id=boards[0].id,
                project_id=projects[0].id,
                creator_id=users[2].id,
                assignee_id=users[2].id,
                last_modifier_id=users[2].id,
                due_date=now + timedelta(days=2),
            ),
            Task(
                title=DEMO_TASKS[1]["title"],
                description=DEMO_TASKS[1]["description"],
                status=DEMO_TASKS[1]["status"],
                order_in_project=0,
                board_id=boards[1].id,
                project_id=projects[1].id,
                creator_id=users[1].id,
                assignee_id=users[2].id,
                last_modifier_id=users[1].id,
                due_date=now + timedelta(days=5),
            ),
            Task(
                title=DEMO_TASKS[2]["title"],
                description=DEMO_TASKS[2]["description"],
                status=DEMO_TASKS[2]["status"],
                order_in_project=0,
                board_id=boards[2].id,
                project_id=projects[2].id,
                creator_id=users[0].id,
                assignee_id=users[1].id,
                last_modifier_id=users[1].id,
                due_date=now + timedelta(days=3),
            ),
        ]
        db.add_all(tasks)
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
