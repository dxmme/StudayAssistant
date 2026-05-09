"""refinement_proposals table

Revision ID: d5e6f7a8b9c0
Revises: b3c9f1a2d456
Create Date: 2026-05-09 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "b3c9f1a2d456"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refinement_proposals",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("concept_id", sa.Text, sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("cards", sa.JSON, nullable=False),
        sa.Column("again_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("completed_at", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("refinement_proposals")
