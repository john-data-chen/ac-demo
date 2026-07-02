"""Shared response serializers (NestJS-compatible shapes)."""

from app.models import User


def user_ref(u: User | None) -> dict | None:
    if not u:
        return None
    return {"_id": str(u.id), "name": u.name, "email": u.email}
