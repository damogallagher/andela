from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://andela:andela@localhost:5432/andela_guardrails"
    app_scan_root: Path = Path.cwd()

    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()

