"""add reset token columns

Revision ID: add_reset_token
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_reset_token'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('reset_token', sa.String(100), unique=True))
    op.add_column('user', sa.Column('reset_token_expiration', sa.DateTime))

def downgrade():
    op.drop_column('user', 'reset_token_expiration')
    op.drop_column('user', 'reset_token') 