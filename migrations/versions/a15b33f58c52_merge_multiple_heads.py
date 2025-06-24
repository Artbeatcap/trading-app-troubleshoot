"""Merge multiple heads

Revision ID: a15b33f58c52
Revises: 19422db95ef8, add_reset_token
Create Date: 2025-06-23 00:43:42.316019

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a15b33f58c52'
down_revision = ('19422db95ef8', 'add_reset_token')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
