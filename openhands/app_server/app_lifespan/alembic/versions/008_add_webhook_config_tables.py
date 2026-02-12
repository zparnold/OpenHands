"""Add webhook_configs and webhook_rules tables

Revision ID: 008
Revises: 007
Create Date: 2026-02-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, Sequence[str], None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create webhook_configs table
    op.create_table(
        'webhook_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('repository_url', sa.String(), nullable=False),
        sa.Column('project_name', sa.String(255), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_user_id', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_webhook_configs_organization_id'),
        'webhook_configs',
        ['organization_id'],
        unique=False,
    )
    op.create_index(
        'ix_webhook_configs_provider_repo',
        'webhook_configs',
        ['provider', 'repository_url'],
        unique=False,
    )

    # Create webhook_rules table
    op.create_table(
        'webhook_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('webhook_config_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['webhook_config_id'], ['webhook_configs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_webhook_rules_webhook_config_id'),
        'webhook_rules',
        ['webhook_config_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_webhook_rules_webhook_config_id'),
        table_name='webhook_rules',
    )
    op.drop_table('webhook_rules')

    op.drop_index(
        'ix_webhook_configs_provider_repo',
        table_name='webhook_configs',
    )
    op.drop_index(
        op.f('ix_webhook_configs_organization_id'),
        table_name='webhook_configs',
    )
    op.drop_table('webhook_configs')
