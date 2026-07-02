import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.main import app
from app.models import User

TEST_DB_URL = "postgresql+psycopg://root:123456@localhost:5432/task_manager"


@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng


@pytest.fixture(scope="module")
def user_ids(test_engine):
    with Session(test_engine) as db:
        u1 = User(email=f"cov1_{uuid.uuid4()}@test.com", name="User Cov 1")
        u2 = User(email=f"cov2_{uuid.uuid4()}@test.com", name="User Cov 2")
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
