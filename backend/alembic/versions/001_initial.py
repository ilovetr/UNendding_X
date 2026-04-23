"""Initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('did', sa.String(512), nullable=True),
        sa.Column('agent_card', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('endpoint', sa.String(512), nullable=True),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', name='agentstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agents_name', 'agents', ['name'])
    op.create_index('ix_agents_did', 'agents', ['did'], unique=True)

    # Groups table
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('privacy', sa.Enum('PUBLIC', 'PRIVATE', name='privacy'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invite_code', sa.String(6), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_groups_name', 'groups', ['name'])
    op.create_index('ix_groups_invite_code', 'groups', ['invite_code'], unique=True)

    # Group members table
    op.create_table(
        'group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Abilities table
    op.create_table(
        'abilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('definition', postgresql.JSONB, nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('hash', sa.String(64), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'DEPRECATED', name='abilitystatus'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_abilities_name', 'abilities', ['name'])

    # Skill tokens table
    op.create_table(
        'skill_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('skill_name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('permissions', postgresql.JSONB, nullable=False),
        sa.Column('token_jti', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_tokens_skill_name', 'skill_tokens', ['skill_name'])
    op.create_index('ix_skill_tokens_token_jti', 'skill_tokens', ['token_jti'], unique=True)

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_agent_id', 'audit_logs', ['agent_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('skill_tokens')
    op.drop_table('abilities')
    op.drop_table('group_members')
    op.drop_table('groups')
    op.drop_table('agents')
