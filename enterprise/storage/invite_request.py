from datetime import datetime

from sqlalchemy import Column, DateTime, Identity, Integer, String
from storage.base import Base


class InviteRequest(Base):  # type: ignore
    """Model for storing user invite requests."""

    __tablename__ = 'invite_requests'

    id = Column(Integer, Identity(), primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    status = Column(
        String, nullable=False, default='pending', index=True
    )  # pending, approved, rejected
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
