"""Add reset token columns to user table (SQLite-safe)

Revision ID: d1add_user_reset_columns
Revises: becbf99ab3eb
Create Date: 2025-08-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1add_user_reset_columns'
down_revision = 'becbf99ab3eb'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('reset_token', sa.String(length=100), unique=True))
        batch_op.add_column(sa.Column('reset_token_expiration', sa.DateTime()))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('reset_token_expiration')
        batch_op.drop_column('reset_token')



