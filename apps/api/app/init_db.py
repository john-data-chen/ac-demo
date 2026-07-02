"""
Run this to create all tables: uv run python -m app.init_db
"""

import app.models  # noqa: F401 — registers all models
from app.database import Base, engine


def create_tables():
    Base.metadata.create_all(engine)
    print("All tables created successfully.")


if __name__ == "__main__":
    create_tables()
