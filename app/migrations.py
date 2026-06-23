from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from alembic import command
from app.database import engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INITIAL_REVISION = "0001_initial_schema"
INITIAL_SCHEMA_TABLES = {"scan_runs", "findings"}
ALEMBIC_VERSION_TABLE = "alembic_version"


def build_alembic_config(connection: Connection | None = None) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def run_migrations() -> None:
    with engine.begin() as connection:
        config = build_alembic_config(connection)
        stamp_existing_initial_schema(connection, config)
        command.upgrade(config, "head")


def reset_database() -> None:
    with engine.begin() as connection:
        config = build_alembic_config(connection)
        command.downgrade(config, "base")
        command.upgrade(config, "head")


def stamp_existing_initial_schema(connection: Connection, config: Config) -> bool:
    """Mark local pre-Alembic databases as migrated without dropping scan history."""
    existing_tables = set(inspect(connection).get_table_names())
    if ALEMBIC_VERSION_TABLE in existing_tables:
        return False
    if not INITIAL_SCHEMA_TABLES.issubset(existing_tables):
        return False

    command.stamp(config, INITIAL_REVISION)
    return True
