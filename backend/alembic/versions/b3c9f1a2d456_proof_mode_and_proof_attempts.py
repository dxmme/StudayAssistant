"""proof_mode_and_proof_attempts

Revision ID: b3c9f1a2d456
Revises: e68e40ed41fe
Create Date: 2026-05-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c9f1a2d456'
down_revision: Union[str, Sequence[str], None] = 'e68e40ed41fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proof_mode', sa.Boolean(), nullable=False, server_default='0'))

    op.create_table(
        'proof_attempts',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('card_id', sa.Text(), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('turns', sa.JSON(), nullable=False),
        sa.Column('final_rating', sa.Integer(), nullable=True),
        sa.Column('credit_score', sa.Float(), nullable=True),
        sa.Column('started_at', sa.Text(), nullable=False),
        sa.Column('finished_at', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('proof_attempts')
    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.drop_column('proof_mode')
