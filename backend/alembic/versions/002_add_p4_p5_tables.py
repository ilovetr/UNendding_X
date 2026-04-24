"""Add P4/P5 tables - skill_usages, refresh_tokens

Revision ID: 002_add_p4_p5_tables
Revises: 001_initial
Create Date: 2026-04-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '002_add_p4_p5_tables'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Refresh tokens table (P3 Token Security)
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_agent_id', 'refresh_tokens', ['agent_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    # Skill usages table (P4 Ability Quota Tracking)
    op.create_table(
        'skill_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issuer_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['token_id'], ['skill_tokens.id']),
        sa.ForeignKeyConstraint(['ability_id'], ['abilities.id']),
        sa.ForeignKeyConstraint(['issuer_agent_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_usages_created_at', 'skill_usages', ['created_at'])
    op.create_index('ix_skill_usages_token_id', 'skill_usages', ['token_id'])
    op.create_index('ix_skill_usages_ability_id', 'skill_usages', ['ability_id'])


def downgrade() -> None:
    op.drop_table('skill_usages')
    op.drop_table('refresh_tokens')
