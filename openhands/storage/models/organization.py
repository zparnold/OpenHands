"""Organization model for multi-tenancy support."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from openhands.app_server.utils.sql_utils import Base


class Organization(Base):
    """Organization model for grouping users into tenants."""

    __tablename__ = 'organizations'

    id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    members = relationship(
        'OrganizationMembership', back_populates='organization', cascade='all, delete-orphan'
    )
    sessions = relationship('Session', back_populates='organization', cascade='all, delete-orphan')
    secrets = relationship('Secret', back_populates='organization', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Organization(id='{self.id}', name='{self.name}')>"


class OrganizationMembership(Base):
    """Organization membership linking users to organizations with roles."""

    __tablename__ = 'organization_memberships'

    id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(String, ForeignKey('organizations.id'), nullable=False, index=True)
    role = Column(String, nullable=False, default='member')  # 'admin' or 'member'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    user = relationship('User', back_populates='organization_memberships')
    organization = relationship('Organization', back_populates='members')

    def __repr__(self):
        return f"<OrganizationMembership(user_id='{self.user_id}', organization_id='{self.organization_id}', role='{self.role}')>"
