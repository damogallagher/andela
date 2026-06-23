from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://andela:andela@localhost:5432/andela_guardrails"
    app_scan_root: Path = Path.cwd()
    upload_max_files: int = Field(default=10, gt=0)
    upload_max_file_size_bytes: int = Field(default=1_048_576, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
