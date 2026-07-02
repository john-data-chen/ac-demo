"""Auth route tests — login, profile, logout."""

import uuid

import pytest

from app.models import User


@pytest.fixture
def test_user(db):
    user = User(email=f"auth_test_{uuid.uuid4()}@test.com", name="Auth User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
