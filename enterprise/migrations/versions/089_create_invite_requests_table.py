"""create invite_requests table

Revision ID: 089
Revises: 088
Create Date: 2025-01-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '089'
down_revision: Union[str, None] = '088'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invite_requests table for storing user invite requests."""
    op.create_table(
        'invite_requests',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False, primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create index on email column
    op.create_index(
        'ix_invite_requests_email',
        'invite_requests',
        ['email'],
        unique=True,
    )

    # Create index on status column for filtering
    op.create_index(
        'ix_invite_requests_status',
        'invite_requests',
        ['status'],
    )


def downgrade() -> None:
    """Drop invite_requests table."""
    op.drop_index('ix_invite_requests_status', table_name='invite_requests')
    op.drop_index('ix_invite_requests_email', table_name='invite_requests')
    op.drop_table('invite_requests')
