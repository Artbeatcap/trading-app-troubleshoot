"""
add plans, plan_alerts, executions, usage_counters

Revision ID: 7f3e0f2b9a6a
Revises: 
Create Date: 2025-10-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7f3e0f2b9a6a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('symbol', sa.String(length=32), nullable=False, index=True),
        sa.Column('scenario_direction', sa.String(length=8)),
        sa.Column('invalidation', sa.Float()),
        sa.Column('targets', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('playbook_tags', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('rr_expected', sa.Float()),
        sa.Column('sizing', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('draft_payload', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    # Note: columns with `index=True` above already cause SQLAlchemy to
    # auto-create indexes named `ix_plans_user_id` and `ix_plans_symbol`
    # as part of create_table(), so no explicit op.create_index() is needed
    # for those. Doing so would raise DuplicateTable on fresh installs.

    op.create_table(
        'plan_alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plan_id', sa.Integer(), nullable=False, index=True),
        sa.Column('type', sa.String(length=32)),
        sa.Column('channel', sa.String(length=16)),
        sa.Column('status', sa.String(length=16), server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_plan_alerts_plan', 'plan_alerts', ['plan_id'])

    op.create_table(
        'executions',
        sa.Column('execution_id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('broker', sa.String(length=16), nullable=False),
        sa.Column('broker_trade_id', sa.String(length=64)),
        sa.Column('account_id', sa.String(length=64)),
        sa.Column('timestamp_utc', sa.DateTime(), nullable=False, index=True),
        sa.Column('symbol', sa.String(length=32), nullable=False, index=True),
        sa.Column('asset_type', sa.String(length=16), nullable=False),
        sa.Column('side', sa.String(length=8), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('commission', sa.Float(), server_default='0'),
        sa.Column('fees', sa.Float(), server_default='0'),
        sa.Column('currency', sa.String(length=8), server_default='USD'),
        sa.Column('right', sa.String(length=1)),
        sa.Column('strike', sa.Float()),
        sa.Column('expiration', sa.Date()),
        sa.Column('multiplier', sa.Integer()),
        sa.Column('occ', sa.String(length=64)),
    )
    op.create_index('ix_exec_user', 'executions', ['user_id'])
    op.create_index('ix_exec_symbol', 'executions', ['symbol'])
    op.create_index('ix_exec_ts', 'executions', ['timestamp_utc'])

    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('count', sa.Integer(), server_default='0'),
    )
    op.create_unique_constraint('uix_usage_user_key_week', 'usage_counters', ['user_id','key','week_start'])


def downgrade():
    op.drop_constraint('uix_usage_user_key_week', 'usage_counters', type_='unique')
    op.drop_table('usage_counters')
    op.drop_index('ix_exec_ts', table_name='executions')
    op.drop_index('ix_exec_symbol', table_name='executions')
    op.drop_index('ix_exec_user', table_name='executions')
    op.drop_table('executions')
    op.drop_index('ix_plan_alerts_plan', table_name='plan_alerts')
    op.drop_table('plan_alerts')
    # ix_plans_symbol and ix_plans_user_id are auto-dropped with the table.
    op.drop_table('plans')



