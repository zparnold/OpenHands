"""Add users, organizations, sessions and secrets tables

Revision ID: 006
Revises: 005
Create Date: 2026-01-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, Sequence[str], None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_organization_memberships_user_id'),
        'organization_memberships',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_organization_memberships_organization_id'),
        'organization_memberships',
        ['organization_id'],
        unique=False,
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('state', sa.JSON(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(
        op.f('ix_sessions_organization_id'), 'sessions', ['organization_id'], unique=False
    )
    op.create_index(
        op.f('ix_sessions_conversation_id'), 'sessions', ['conversation_id'], unique=False
    )

    # Create secrets table
    op.create_table(
        'secrets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_secrets_user_id'), 'secrets', ['user_id'], unique=False)
    op.create_index(
        op.f('ix_secrets_organization_id'), 'secrets', ['organization_id'], unique=False
    )
    op.create_index(op.f('ix_secrets_key'), 'secrets', ['key'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_secrets_key'), table_name='secrets')
    op.drop_index(op.f('ix_secrets_organization_id'), table_name='secrets')
    op.drop_index(op.f('ix_secrets_user_id'), table_name='secrets')
    op.drop_table('secrets')

    op.drop_index(op.f('ix_sessions_conversation_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_organization_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')

    op.drop_index(
        op.f('ix_organization_memberships_organization_id'),
        table_name='organization_memberships',
    )
    op.drop_index(
        op.f('ix_organization_memberships_user_id'), table_name='organization_memberships'
    )
    op.drop_table('organization_memberships')

    op.drop_table('organizations')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
