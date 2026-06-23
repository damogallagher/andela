from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://andela@localhost:5432/andela_guardrails"
    app_scan_root: Path = Path.cwd()
    upload_max_files: int = Field(default=10, gt=0)
    upload_max_file_size_bytes: int = Field(default=1_048_576, gt=0)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
