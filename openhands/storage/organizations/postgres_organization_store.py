"""PostgreSQL-backed organization store helpers."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from openhands.storage.models.organization import Organization, OrganizationMembership

logger = logging.getLogger(__name__)

DEFAULT_ORG_ROLE = 'admin'
DEFAULT_ORGANIZATION_ID = os.environ.get('DEFAULT_ORGANIZATION_ID', '')


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
    """Helpers for organization and membership management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Default org helper ──────────────────────────────────────────

    async def ensure_default_org_for_user(
        self,
        user_id: str,
        email: str | None = None,
        display_name: str | None = None,
        role: str = DEFAULT_ORG_ROLE,
    ) -> Organization:
        """Ensure the user belongs to a default organization.

        When ``DEFAULT_ORGANIZATION_ID`` is set, new users are added to the
        shared organization as ``member`` instead of creating a personal org.
        Otherwise a new personal organization is created with the user as admin.
        """
        if not user_id:
            raise ValueError('user_id is required to ensure organization membership')

        # When a shared org is configured, check membership in that org first
        shared_org_id = DEFAULT_ORGANIZATION_ID
        if shared_org_id:
            membership = await self.get_membership(user_id, shared_org_id)
            if membership:
                org = await self.session.get(Organization, shared_org_id)
                if org:
                    return org

            # User is not yet a member of the shared org — add them
            org = await self.session.get(Organization, shared_org_id)
            if org:
                self.session.add(
                    OrganizationMembership(
                        id=str(uuid4()),
                        user_id=user_id,
                        organization_id=shared_org_id,
                        role='member',
                    )
                )
                logger.info(
                    'User %s auto-joined shared org %s as member',
                    user_id,
                    shared_org_id,
                )
                return org
            logger.warning(
                'DEFAULT_ORGANIZATION_ID %s not found, falling back to personal org',
                shared_org_id,
            )

        # Fallback: check for any existing membership
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

        # Create a new personal organization
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

    # ── Organization CRUD ───────────────────────────────────────────

    async def get_organization(self, org_id: str) -> Organization | None:
        """Get an organization by ID."""
        return await self.session.get(Organization, org_id)

    async def update_organization(self, org_id: str, name: str) -> Organization | None:
        """Update an organization's name. Returns None if not found."""
        org = await self.session.get(Organization, org_id)
        if org is None:
            return None
        org.name = name
        return org

    # ── Membership queries ──────────────────────────────────────────

    async def get_membership(
        self, user_id: str, org_id: str
    ) -> OrganizationMembership | None:
        """Get a user's membership in a specific organization."""
        result = await self.session.execute(
            select(OrganizationMembership).where(
                and_(
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.organization_id == org_id,
                )
            )
        )
        return result.scalars().first()

    async def list_org_members(self, org_id: str) -> list[OrganizationMembership]:
        """List all members of an organization (with user relationship loaded)."""
        result = await self.session.execute(
            select(OrganizationMembership)
            .options(joinedload(OrganizationMembership.user))
            .where(OrganizationMembership.organization_id == org_id)
        )
        return list(result.scalars().unique().all())

    async def list_user_organizations(self, user_id: str) -> list[Organization]:
        """List all organizations a user belongs to."""
        result = await self.session.execute(
            select(Organization)
            .join(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
        )
        return list(result.scalars().all())

    # ── Membership mutations ────────────────────────────────────────

    async def add_member(
        self, org_id: str, user_id: str, role: str = 'member'
    ) -> OrganizationMembership:
        """Add a user to an organization. Raises ValueError if already a member."""
        existing = await self.get_membership(user_id, org_id)
        if existing is not None:
            raise ValueError(
                f'User {user_id} is already a member of organization {org_id}'
            )
        membership = OrganizationMembership(
            id=str(uuid4()),
            user_id=user_id,
            organization_id=org_id,
            role=role,
        )
        self.session.add(membership)
        return membership

    async def update_member_role(
        self, org_id: str, user_id: str, role: str
    ) -> OrganizationMembership | None:
        """Update a member's role. Returns None if not a member."""
        membership = await self.get_membership(user_id, org_id)
        if membership is None:
            return None
        membership.role = role
        return membership

    async def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a member from an organization.

        Returns False if the user is not a member. Raises ValueError if the
        user is the last admin (to prevent orphaned organizations).
        """
        membership = await self.get_membership(user_id, org_id)
        if membership is None:
            return False

        # Prevent removing the last admin
        if membership.role == 'admin':
            admin_count_result = await self.session.execute(
                select(func.count())
                .select_from(OrganizationMembership)
                .where(
                    and_(
                        OrganizationMembership.organization_id == org_id,
                        OrganizationMembership.role == 'admin',
                    )
                )
            )
            admin_count = admin_count_result.scalar() or 0
            if admin_count <= 1:
                raise ValueError('Cannot remove the last admin from an organization')

        await self.session.execute(
            delete(OrganizationMembership).where(
                and_(
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.organization_id == org_id,
                )
            )
        )
        return True
