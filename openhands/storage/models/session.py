"""Session model for persistent storage."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from openhands.app_server.utils.sql_utils import Base


class Session(Base):
    """Session model for persistent session state linked to users/organizations."""

    __tablename__ = 'sessions'

    id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(
        String, ForeignKey('organizations.id'), nullable=True, index=True
    )
    conversation_id = Column(String, nullable=True, index=True)
    state = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_accessed_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user = relationship('User', back_populates='sessions')
    organization = relationship('Organization', back_populates='sessions')

    def __repr__(self):
        return f"<Session(id='{self.id}', user_id='{self.user_id}', organization_id='{self.organization_id}')>"
