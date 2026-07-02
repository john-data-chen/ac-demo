from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    node_env: str = "development"
    jwt_secret: str = "dev-secret-change-in-production!"
    database_url: str = "postgresql+psycopg://root:123456@localhost:5432/task_manager"
    next_public_web_url: str = "http://localhost:3000"
    port: int = 3001

    @field_validator("database_url")
    @classmethod
    def force_psycopg_driver(cls, v: str) -> str:
        # ponytail: managed Postgres providers (Neon, Vercel Postgres) hand out
        # plain postgresql:// URLs, which SQLAlchemy defaults to psycopg2 (not installed)
        if v.startswith(("postgresql://", "postgres://")):
            return "postgresql+psycopg://" + v.split("://", 1)[1]
        return v


settings = Settings()
