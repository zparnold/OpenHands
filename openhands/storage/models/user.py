"""User model for persistent storage."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from openhands.app_server.utils.sql_utils import Base


class User(Base):
    """User model for storing user identities."""

    __tablename__ = 'users'

    id = Column(String, primary_key=True, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    sessions = relationship('Session', back_populates='user', cascade='all, delete-orphan')
    secrets = relationship('Secret', back_populates='user', cascade='all, delete-orphan')
    organization_memberships = relationship(
        'OrganizationMembership', back_populates='user', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', display_name='{self.display_name}')>"
