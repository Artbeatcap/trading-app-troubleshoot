"""journal model update

Revision ID: 5b7bf561026e
Revises: cce21cf37edb
Create Date: 2025-06-09 22:38:58.511508

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b7bf561026e'
down_revision = 'cce21cf37edb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user')
    op.drop_table('trading_journal')
    op.drop_table('trade_analysis')
    op.drop_table('user_settings')
    op.drop_table('trade')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('trade',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
    sa.Column('trade_type', sa.VARCHAR(length=20), nullable=False),
    sa.Column('entry_date', sa.DATETIME(), nullable=False),
    sa.Column('exit_date', sa.DATETIME(), nullable=True),
    sa.Column('entry_price', sa.FLOAT(), nullable=False),
    sa.Column('quantity', sa.INTEGER(), nullable=False),
    sa.Column('entry_reason', sa.TEXT(), nullable=True),
    sa.Column('exit_price', sa.FLOAT(), nullable=True),
    sa.Column('exit_reason', sa.TEXT(), nullable=True),
    sa.Column('strike_price', sa.FLOAT(), nullable=True),
    sa.Column('expiration_date', sa.DATE(), nullable=True),
    sa.Column('option_type', sa.VARCHAR(length=10), nullable=True),
    sa.Column('premium_paid', sa.FLOAT(), nullable=True),
    sa.Column('implied_volatility', sa.FLOAT(), nullable=True),
    sa.Column('is_spread', sa.BOOLEAN(), nullable=True),
    sa.Column('spread_type', sa.VARCHAR(length=30), nullable=True),
    sa.Column('long_strike', sa.FLOAT(), nullable=True),
    sa.Column('short_strike', sa.FLOAT(), nullable=True),
    sa.Column('long_premium', sa.FLOAT(), nullable=True),
    sa.Column('short_premium', sa.FLOAT(), nullable=True),
    sa.Column('net_credit', sa.FLOAT(), nullable=True),
    sa.Column('max_profit', sa.FLOAT(), nullable=True),
    sa.Column('max_loss', sa.FLOAT(), nullable=True),
    sa.Column('breakeven_price', sa.FLOAT(), nullable=True),
    sa.Column('delta', sa.FLOAT(), nullable=True),
    sa.Column('gamma', sa.FLOAT(), nullable=True),
    sa.Column('theta', sa.FLOAT(), nullable=True),
    sa.Column('vega', sa.FLOAT(), nullable=True),
    sa.Column('underlying_price_at_entry', sa.FLOAT(), nullable=True),
    sa.Column('underlying_price_at_exit', sa.FLOAT(), nullable=True),
    sa.Column('profit_loss', sa.FLOAT(), nullable=True),
    sa.Column('profit_loss_percent', sa.FLOAT(), nullable=True),
    sa.Column('market_condition', sa.VARCHAR(length=50), nullable=True),
    sa.Column('setup_type', sa.VARCHAR(length=100), nullable=True),
    sa.Column('timeframe', sa.VARCHAR(length=20), nullable=True),
    sa.Column('stop_loss', sa.FLOAT(), nullable=True),
    sa.Column('take_profit', sa.FLOAT(), nullable=True),
    sa.Column('risk_amount', sa.FLOAT(), nullable=True),
    sa.Column('notes', sa.TEXT(), nullable=True),
    sa.Column('tags', sa.VARCHAR(length=200), nullable=True),
    sa.Column('entry_chart_image', sa.VARCHAR(length=200), nullable=True),
    sa.Column('exit_chart_image', sa.VARCHAR(length=200), nullable=True),
    sa.Column('is_analyzed', sa.BOOLEAN(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_settings',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('auto_analyze_trades', sa.BOOLEAN(), nullable=True),
    sa.Column('auto_create_journal', sa.BOOLEAN(), nullable=True),
    sa.Column('analysis_detail_level', sa.VARCHAR(length=20), nullable=True),
    sa.Column('daily_journal_reminder', sa.BOOLEAN(), nullable=True),
    sa.Column('weekly_summary', sa.BOOLEAN(), nullable=True),
    sa.Column('default_chart_timeframe', sa.VARCHAR(length=10), nullable=True),
    sa.Column('trades_per_page', sa.INTEGER(), nullable=True),
    sa.Column('default_risk_percent', sa.FLOAT(), nullable=True),
    sa.Column('max_daily_loss', sa.FLOAT(), nullable=True),
    sa.Column('max_position_size', sa.FLOAT(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('trade_analysis',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('trade_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('overall_score', sa.INTEGER(), nullable=True),
    sa.Column('strengths', sa.TEXT(), nullable=True),
    sa.Column('weaknesses', sa.TEXT(), nullable=True),
    sa.Column('improvement_areas', sa.TEXT(), nullable=True),
    sa.Column('actionable_drills', sa.TEXT(), nullable=True),
    sa.Column('entry_analysis', sa.TEXT(), nullable=True),
    sa.Column('exit_analysis', sa.TEXT(), nullable=True),
    sa.Column('risk_analysis', sa.TEXT(), nullable=True),
    sa.Column('market_context', sa.TEXT(), nullable=True),
    sa.Column('options_analysis', sa.TEXT(), nullable=True),
    sa.Column('chart_analysis', sa.TEXT(), nullable=True),
    sa.Column('recommendations', sa.TEXT(), nullable=True),
    sa.Column('key_lessons', sa.TEXT(), nullable=True),
    sa.Column('future_setups', sa.TEXT(), nullable=True),
    sa.Column('analysis_date', sa.DATETIME(), nullable=True),
    sa.Column('ai_model_used', sa.VARCHAR(length=50), nullable=True),
    sa.ForeignKeyConstraint(['trade_id'], ['trade.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trading_journal',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('journal_date', sa.DATE(), nullable=False),
    sa.Column('daily_pnl', sa.FLOAT(), nullable=True),
    sa.Column('market_outlook', sa.TEXT(), nullable=True),
    sa.Column('daily_goals', sa.TEXT(), nullable=True),
    sa.Column('what_went_well', sa.TEXT(), nullable=True),
    sa.Column('what_went_wrong', sa.TEXT(), nullable=True),
    sa.Column('lessons_learned', sa.TEXT(), nullable=True),
    sa.Column('tomorrow_focus', sa.TEXT(), nullable=True),
    sa.Column('emotional_state', sa.VARCHAR(length=50), nullable=True),
    sa.Column('stress_level', sa.INTEGER(), nullable=True),
    sa.Column('discipline_score', sa.INTEGER(), nullable=True),
    sa.Column('ai_daily_feedback', sa.TEXT(), nullable=True),
    sa.Column('daily_score', sa.INTEGER(), nullable=True),
    sa.Column('market_trend', sa.VARCHAR(length=50), nullable=True),
    sa.Column('volatility', sa.VARCHAR(length=20), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('journal_date')
    )
    op.create_table('user',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('username', sa.VARCHAR(length=80), nullable=False),
    sa.Column('email', sa.VARCHAR(length=120), nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=128), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('default_risk_percent', sa.FLOAT(), nullable=True),
    sa.Column('account_size', sa.FLOAT(), nullable=True),
    sa.Column('email_verified', sa.BOOLEAN(), nullable=True),
    sa.Column('email_verification_token', sa.VARCHAR(length=100), nullable=True),
    sa.Column('token_generated_at', sa.DATETIME(), nullable=True),
    sa.Column('password_reset_token', sa.VARCHAR(length=100), nullable=True),
    sa.Column('password_reset_token_generated_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('email_verification_token'),
    sa.UniqueConstraint('password_reset_token'),
    sa.UniqueConstraint('username')
    )
    # ### end Alembic commands ###
