"""add pipeline_runs table

Revision ID: a00e2d059c17
Revises: 001_initial_schema
Create Date: 2026-08-26 10:58:09.738953
"""

from alembic import op
import sqlalchemy as sa


revision: str = 'a00e2d059c17'
down_revision: str | None = '001_initial_schema'


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("history_hours", sa.Integer(), nullable=False),
        sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "succeeded", "failed", name="pipeline_run_status"),
            nullable=False,
        ),
        sa.Column("city_count", sa.Integer(), nullable=True),
        sa.Column("raw_response_count", sa.Integer(), nullable=True),
        sa.Column("gold_row_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    sa.Enum(name="pipeline_run_status").drop(op.get_bind())