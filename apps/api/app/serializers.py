"""Shared response serializers (NestJS-compatible shapes)."""

from app.models import Project, User


def user_ref(u: User | None) -> dict | None:
    if not u:
        return None
    return {"_id": str(u.id), "name": u.name, "email": u.email}


def project_ref(p: Project) -> dict:
    return {"_id": str(p.id), "title": p.title}
