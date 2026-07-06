import jwt
import pytest

from app.config import settings

# Shared fixtures are now in conftest.py


@pytest.mark.asyncio
async def test_users_router(client, user_ids):
    email1, _, _, _ = user_ids
    async with client as c:
        token = (await c.post("/auth/login", json={"email": email1})).json()["access_token"]

        # Test find_all
        r_all = await c.get("/users", headers={"Cookie": f"jwt={token}"})
        assert r_all.status_code == 200
        assert len(r_all.json()["users"]) >= 2

        # Test search
        r_search = await c.get("/users/search?username=Cov", headers={"Cookie": f"jwt={token}"})
        assert r_search.status_code == 200
        assert len(r_search.json()["users"]) >= 2


@pytest.mark.asyncio
async def test_auth_exceptions(client, user_ids, test_engine):
    email1, _, _, _ = user_ids

    async with client as c:
        # 401 Missing token
        r_miss = await c.get("/users")
        assert r_miss.status_code == 401

        # 401 Invalid token
        r_inv = await c.get("/users", headers={"Cookie": f"jwt={'invalid-token-string'}"})
        assert r_inv.status_code == 401

        # 401 Expired token
        expired_token = jwt.encode(
            {"email": email1, "exp": 1}, settings.jwt_secret.get_secret_value(), algorithm="HS256"
        )
        r_exp = await c.get("/users", headers={"Cookie": f"jwt={expired_token}"})
        assert r_exp.status_code == 401

        # 401 User not found
        fake_token = jwt.encode(
            {"email": "doesnotexist@fake.com"},
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        r_notfound = await c.get("/users", headers={"Cookie": f"jwt={fake_token}"})
        assert r_notfound.status_code == 401
