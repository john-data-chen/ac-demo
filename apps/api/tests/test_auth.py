"""Auth route tests — login, profile, logout."""

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
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def test_user(db):
    user = User(email=f"auth_test_{uuid.uuid4()}@test.com", name="Auth User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client(engine):
    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    async with client as c:
        r = await c.post("/auth/login", json={"email": test_user.email})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email
    assert "jwt" in r.cookies


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    async with client as c:
        r = await c.post("/auth/login", json={"email": "nobody@nowhere.com"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_profile_with_cookie(client, test_user):
    async with client as c:
        login = await c.post("/auth/login", json={"email": test_user.email})
        token = login.json()["access_token"]
        r = await c.get("/auth/profile", headers={"Cookie": f"jwt={token}"})
    assert r.status_code == 200
    assert r.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_profile_unauthorized(client):
    async with client as c:
        r = await c.get("/auth/profile")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, test_user):
    async with client as c:
        login = await c.post("/auth/login", json={"email": test_user.email})
        token = login.json()["access_token"]
        r = await c.post("/auth/logout", headers={"Cookie": f"jwt={token}"})
    assert r.status_code == 200
    assert r.json()["message"] == "Successfully logged out"
