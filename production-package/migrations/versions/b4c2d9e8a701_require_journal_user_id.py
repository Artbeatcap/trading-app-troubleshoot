"""Require journal entries to belong to a user

Revision ID: b4c2d9e8a701
Revises: d1add_user_reset_columns
Create Date: 2026-05-02 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c2d9e8a701'
down_revision = 'd1add_user_reset_columns'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM trading_journal WHERE user_id IS NULL")
    with op.batch_alter_table('trading_journal', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table('trading_journal', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=True,
        )
