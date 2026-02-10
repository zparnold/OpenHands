"""Add conversation_events table for Postgres-backed event storage

Revision ID: 007
Revises: 006
Create Date: 2026-02-09 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, Sequence[str], None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'conversation_events',
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('event_id'),
    )
    op.create_index(
        op.f('ix_conversation_events_conversation_id'),
        'conversation_events',
        ['conversation_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversation_events_user_id'),
        'conversation_events',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversation_events_kind'),
        'conversation_events',
        ['kind'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversation_events_timestamp'),
        'conversation_events',
        ['timestamp'],
        unique=False,
    )
    op.create_index(
        'ix_conversation_events_conversation_timestamp',
        'conversation_events',
        ['conversation_id', 'timestamp'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_conversation_events_conversation_timestamp',
        table_name='conversation_events',
    )
    op.drop_index(
        op.f('ix_conversation_events_timestamp'),
        table_name='conversation_events',
    )
    op.drop_index(
        op.f('ix_conversation_events_kind'),
        table_name='conversation_events',
    )
    op.drop_index(
        op.f('ix_conversation_events_user_id'),
        table_name='conversation_events',
    )
    op.drop_index(
        op.f('ix_conversation_events_conversation_id'),
        table_name='conversation_events',
    )
    op.drop_table('conversation_events')
