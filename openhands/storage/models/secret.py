"""Secret model for secure storage of API keys and tokens."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from openhands.app_server.utils.sql_utils import Base, StoredSecretStr


class Secret(Base):
    """Secret model for secure, encrypted storage of third-party API keys."""

    __tablename__ = 'secrets'

    id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=True, index=True)
    organization_id = Column(
        String, ForeignKey('organizations.id'), nullable=True, index=True
    )
    key = Column(String, nullable=False, index=True)
    value = Column(StoredSecretStr, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user = relationship('User', back_populates='secrets')
    organization = relationship('Organization', back_populates='secrets')

    def __repr__(self):
        return f"<Secret(id='{self.id}', key='{self.key}', user_id='{self.user_id}', organization_id='{self.organization_id}')>"
