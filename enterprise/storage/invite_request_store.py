from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import sessionmaker
from storage.invite_request import InviteRequest

from openhands.core.logger import openhands_logger as logger


class InviteRequestStore:
    """Store for managing invite requests."""

    def __init__(self, session_maker: sessionmaker):
        self.session_maker = session_maker

    def create_invite_request(self, email: str, notes: Optional[str] = None) -> bool:
        """
        Create a new invite request.

        Args:
            email: Email address of the user requesting an invite
            notes: Optional notes from the user

        Returns:
            bool: True if created successfully, False if email already exists
        """
        try:
            with self.session_maker() as session:
                # Check if email already exists
                existing = (
                    session.query(InviteRequest)
                    .filter(InviteRequest.email == email.lower())
                    .first()
                )

                if existing:
                    logger.info(
                        f'Invite request already exists for email: {email}',
                        extra={'email': email, 'status': existing.status},
                    )
                    return False

                invite_request = InviteRequest(
                    email=email.lower(),
                    status='pending',
                    notes=notes,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                session.add(invite_request)
                session.commit()
                logger.info(
                    f'Created invite request for email: {email}',
                    extra={'email': email},
                )
                return True
        except Exception as e:
            logger.exception(
                f'Error creating invite request for email: {email}',
                extra={'email': email, 'error': str(e)},
            )
            return False

    def get_invite_requests(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InviteRequest]:
        """
        Get invite requests with optional filtering.

        Args:
            status: Optional status filter (pending, approved, rejected)
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of InviteRequest objects
        """
        try:
            with self.session_maker() as session:
                query = session.query(InviteRequest)

                if status:
                    query = query.filter(InviteRequest.status == status)

                query = query.order_by(desc(InviteRequest.created_at))
                query = query.limit(limit).offset(offset)

                return query.all()
        except Exception as e:
            logger.exception(
                'Error retrieving invite requests',
                extra={'status': status, 'error': str(e)},
            )
            return []

    def update_invite_status(
        self, email: str, status: str, notes: Optional[str] = None
    ) -> bool:
        """
        Update the status of an invite request.

        Args:
            email: Email address of the invite request
            status: New status (pending, approved, rejected)
            notes: Optional notes about the status change

        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            with self.session_maker() as session:
                invite_request = (
                    session.query(InviteRequest)
                    .filter(InviteRequest.email == email.lower())
                    .first()
                )

                if not invite_request:
                    logger.warning(
                        f'Invite request not found for email: {email}',
                        extra={'email': email},
                    )
                    return False

                invite_request.status = status
                invite_request.updated_at = datetime.now(timezone.utc)

                if notes:
                    invite_request.notes = notes

                session.commit()
                logger.info(
                    f'Updated invite request status for email: {email}',
                    extra={'email': email, 'status': status},
                )
                return True
        except Exception as e:
            logger.exception(
                f'Error updating invite request for email: {email}',
                extra={'email': email, 'error': str(e)},
            )
            return False

    def get_invite_request_by_email(self, email: str) -> Optional[InviteRequest]:
        """
        Get an invite request by email address.

        Args:
            email: Email address to search for

        Returns:
            InviteRequest object if found, None otherwise
        """
        try:
            with self.session_maker() as session:
                return (
                    session.query(InviteRequest)
                    .filter(InviteRequest.email == email.lower())
                    .first()
                )
        except Exception as e:
            logger.exception(
                f'Error retrieving invite request for email: {email}',
                extra={'email': email, 'error': str(e)},
            )
            return None

    def count_invite_requests(self, status: Optional[str] = None) -> int:
        """
        Count the number of invite requests with optional status filter.

        Args:
            status: Optional status filter (pending, approved, rejected)

        Returns:
            int: Number of matching invite requests
        """
        try:
            with self.session_maker() as session:
                query = session.query(InviteRequest)

                if status:
                    query = query.filter(InviteRequest.status == status)

                return query.count()
        except Exception as e:
            logger.exception(
                'Error counting invite requests',
                extra={'status': status, 'error': str(e)},
            )
            return 0
