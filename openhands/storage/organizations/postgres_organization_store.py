"""PostgreSQL-backed organization store helpers."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.storage.models.organization import Organization, OrganizationMembership

logger = logging.getLogger(__name__)

DEFAULT_ORG_ROLE = 'admin'


def build_default_org_name(
    user_id: str,
    email: str | None = None,
    display_name: str | None = None,
) -> str:
    """Build a reasonable default organization name for a user."""
    candidate = display_name.strip() if display_name else ''
    if not candidate and email:
        candidate = email.split('@')[0].strip() or email.strip()
    if not candidate:
        candidate = user_id
    return f'{candidate} Organization'


class PostgresOrganizationStore:
    """Helpers for default organization membership management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_default_org_for_user(
        self,
        user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        role: str = DEFAULT_ORG_ROLE,
    ) -> Organization:
        """Ensure the user belongs to a default organization.

        This method creates a new organization and membership if none exist,
        otherwise it returns the existing organization.
        """
        if not user_id:
            raise ValueError('user_id is required to ensure organization membership')

        result = await self.session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id
            )
        )
        membership = result.scalars().first()
        if membership:
            organization = await self.session.get(
                Organization, membership.organization_id
            )
            if organization:
                return organization
            organization = Organization(
                id=membership.organization_id,
                name=build_default_org_name(user_id, email, display_name),
            )
            self.session.add(organization)
            return organization

        organization = Organization(
            id=str(uuid4()),
            name=build_default_org_name(user_id, email, display_name),
        )
        self.session.add(organization)
        self.session.add(
            OrganizationMembership(
                id=str(uuid4()),
                user_id=user_id,
                organization_id=organization.id,
                role=role,
            )
        )
        return organization
