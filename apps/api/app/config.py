from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    node_env: str = "development"
    jwt_secret: str = "dev-secret-change-in-production"
    database_url: str = "postgresql+psycopg://root:123456@localhost:5432/task_manager"
    next_public_web_url: str = "http://localhost:3000"
    port: int = 3001


settings = Settings()
