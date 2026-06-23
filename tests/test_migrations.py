import os

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.database import build_engine
from app.migrations import INITIAL_REVISION, build_alembic_config, stamp_existing_initial_schema


def _drop_schema(connection) -> None:
    connection.execute(text("DROP TABLE IF EXISTS alembic_version, findings, scan_runs CASCADE"))


def _create_pre_alembic_initial_schema(connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE scan_runs (
                id SERIAL NOT NULL,
                label VARCHAR(120) NOT NULL,
                target_path VARCHAR(500) NOT NULL,
                risk_score INTEGER NOT NULL,
                files_scanned INTEGER NOT NULL,
                findings_count INTEGER NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                PRIMARY KEY (id)
            )
            """
        )
    )
    connection.execute(text("CREATE INDEX ix_scan_runs_id ON scan_runs (id)"))
    connection.execute(
        text(
            """
            CREATE TABLE findings (
                id SERIAL NOT NULL,
                scan_run_id INTEGER NOT NULL,
                rule_id VARCHAR(80) NOT NULL,
                title VARCHAR(180) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                line_number INTEGER NOT NULL,
                resource VARCHAR(180) NOT NULL,
                evidence TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                FOREIGN KEY(scan_run_id) REFERENCES scan_runs (id),
                PRIMARY KEY (id)
            )
            """
        )
    )
    connection.execute(text("CREATE INDEX ix_findings_id ON findings (id)"))


def test_stamps_existing_pre_alembic_initial_schema() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])

    with engine.begin() as connection:
        _drop_schema(connection)
        try:
            _create_pre_alembic_initial_schema(connection)
            config = build_alembic_config(connection)

            assert stamp_existing_initial_schema(connection, config) is True

            existing_tables = set(inspect(connection).get_table_names())
            assert "alembic_version" in existing_tables
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert revision == INITIAL_REVISION

            command.upgrade(config, "head")
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == INITIAL_REVISION
        finally:
            _drop_schema(connection)


def test_does_not_stamp_empty_schema() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])

    with engine.begin() as connection:
        _drop_schema(connection)
        config = build_alembic_config(connection)

        assert stamp_existing_initial_schema(connection, config) is False
        assert "alembic_version" not in set(inspect(connection).get_table_names())


def test_build_engine_rejects_non_postgres_urls() -> None:
    with pytest.raises(ValueError, match="Only PostgreSQL database URLs are supported"):
        build_engine("mysql://andela@localhost/andela_guardrails")
