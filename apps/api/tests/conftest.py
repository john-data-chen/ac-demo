import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Board, Project, Task, User

# All test-created users must use this domain so session teardown can find them.
TEST_EMAIL_DOMAIN = "@test.com"


@pytest.fixture(scope="session")
def test_engine():
    # settings.database_url honors the DATABASE_URL env var (CI) and .env (local)
    eng = create_engine(settings.database_url)
    Base.metadata.create_all(eng)
    yield eng
    # Teardown: tests run against the shared dev DB, so delete everything the
    # test users own (tasks → projects → boards → users; owner_id has no
    # ON DELETE CASCADE).
    with Session(eng) as db:
        users = db.query(User).filter(User.email.like(f"%{TEST_EMAIL_DOMAIN}")).all()
        ids = [u.id for u in users]
        if ids:
            for t in db.query(Task).filter(
                (Task.creator_id.in_(ids))
                | (Task.assignee_id.in_(ids))
                | (Task.last_modifier_id.in_(ids))
            ):
                db.delete(t)
            db.flush()
            for p in db.query(Project).filter(Project.owner_id.in_(ids)):
                db.delete(p)
            db.flush()
            for b in db.query(Board).filter(Board.owner_id.in_(ids)):
                db.delete(b)
            db.flush()
            for u in users:
                db.delete(u)
            db.commit()


@pytest.fixture
def db(test_engine):
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="module")
def user_ids(test_engine):
    """Create two users, return their (email1, id1, email2, id2)."""
    with Session(test_engine) as db:
        u1 = User(email=f"u1_{uuid.uuid4()}@test.com", name="User Cov 1")
        u2 = User(email=f"u2_{uuid.uuid4()}@test.com", name="User Cov 2")
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
