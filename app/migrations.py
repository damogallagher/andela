from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Connection

from alembic import command
from alembic.config import Config
from app.database import engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_alembic_config(connection: Connection | None = None) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def run_migrations() -> None:
    with engine.begin() as connection:
        command.upgrade(build_alembic_config(connection), "head")


def reset_database() -> None:
    with engine.begin() as connection:
        config = build_alembic_config(connection)
        command.downgrade(config, "base")
        command.upgrade(config, "head")
