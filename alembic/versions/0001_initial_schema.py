"""Initial scan history schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-23 00:45:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("target_path", sa.String(length=500), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("files_scanned", sa.Integer(), nullable=False),
        sa.Column("findings_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_runs_id"), "scan_runs", ["id"], unique=False)
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("resource", sa.String(length=180), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_findings_id"), "findings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_id"), table_name="findings")
    op.drop_table("findings")
    op.drop_index(op.f("ix_scan_runs_id"), table_name="scan_runs")
    op.drop_table("scan_runs")
