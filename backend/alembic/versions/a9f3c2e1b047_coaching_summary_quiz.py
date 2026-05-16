"""coaching_summary_quiz

Revision ID: a9f3c2e1b047
Revises: 7b336b90db62
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f3c2e1b047'
down_revision: Union[str, Sequence[str], None] = '7b336b90db62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the end-of-session summary + quiz columns to coaching_sessions."""
    with op.batch_alter_table("coaching_sessions") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("quiz", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop the summary + quiz columns."""
    with op.batch_alter_table("coaching_sessions") as batch_op:
        batch_op.drop_column("quiz")
        batch_op.drop_column("summary")
