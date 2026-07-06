from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    node_env: Literal["development", "test", "production"] = "development"
    jwt_secret: SecretStr
    database_url: str
    next_public_web_url: str = "http://localhost:3000"
    port: int = 3001

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_strength(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("jwt_secret must be at least 32 characters")
        return v

    @field_validator("database_url")
    @classmethod
    def force_psycopg_driver(cls, v: str) -> str:
        # ponytail: managed Postgres providers (Neon, Vercel Postgres) hand out
        # plain postgresql:// URLs, which SQLAlchemy defaults to psycopg2 (not installed)
        if v.startswith(("postgresql://", "postgres://")):
            return "postgresql+psycopg://" + v.split("://", 1)[1]
        return v


settings = Settings()
