"""Initial schema: requests + request_metrics

Revision ID: 001
Revises:
Create Date: 2026-04-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("request_type", sa.String(16), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_token_count", sa.Integer(), nullable=True),
        sa.Column("requested_output_tokens", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requests_model", "requests", ["model"])
    op.create_index("ix_requests_created_at", "requests", ["created_at"])

    op.create_table(
        "request_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("queue_ms", sa.Float(), nullable=True),
        sa.Column("ttft_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("tokens_per_sec", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_metrics_request_id", "request_metrics", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_request_metrics_request_id", table_name="request_metrics")
    op.drop_table("request_metrics")
    op.drop_index("ix_requests_created_at", table_name="requests")
    op.drop_index("ix_requests_model", table_name="requests")
    op.drop_table("requests")
