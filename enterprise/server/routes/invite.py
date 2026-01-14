"""API routes for invite request management."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from server.auth.saas_user_auth import SaasUserAuth
from storage.database import session_maker
from storage.invite_request_store import InviteRequestStore

from openhands.core.logger import openhands_logger as logger
from openhands.server.user_auth.user_auth import get_user_auth

invite_router = APIRouter(prefix='/api/invite')


class InviteRequestCreate(BaseModel):
    """Request model for creating an invite request."""

    email: EmailStr
    notes: Optional[str] = None


class InviteRequestResponse(BaseModel):
    """Response model for invite requests."""

    id: int
    email: str
    status: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class InviteRequestStatusUpdate(BaseModel):
    """Request model for updating invite request status."""

    status: str  # pending, approved, rejected
    notes: Optional[str] = None


@invite_router.post('/request', status_code=status.HTTP_201_CREATED)
async def create_invite_request(request: Request, invite_data: InviteRequestCreate):
    """
    Create a new invite request (public endpoint for logged-out users).

    Args:
        request: The FastAPI request object
        invite_data: The invite request data

    Returns:
        Success message
    """
    try:
        store = InviteRequestStore(session_maker)
        success = store.create_invite_request(
            email=invite_data.email.lower(), notes=invite_data.notes
        )

        if not success:
            # Email already exists
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='An invite request with this email already exists',
            )

        logger.info(
            'Invite request created',
            extra={'email': invite_data.email},
        )

        return {
            'message': 'Invite request submitted successfully. You will be notified when your request is reviewed.'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            'Error creating invite request',
            extra={'email': invite_data.email, 'error': str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to create invite request',
        )


@invite_router.get('/requests', response_model=List[InviteRequestResponse])
async def get_invite_requests(
    request: Request,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get all invite requests (admin only endpoint).

    Args:
        request: The FastAPI request object
        status_filter: Optional status filter (pending, approved, rejected)
        limit: Maximum number of results to return
        offset: Number of results to skip

    Returns:
        List of invite requests
    """
    try:
        # Verify user is authenticated
        user_auth: SaasUserAuth = await get_user_auth(request)
        user_id = await user_auth.get_user_id()

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication required',
            )

        # TODO: Add admin role check here when role-based access control is implemented
        # For now, any authenticated user can view invite requests

        store = InviteRequestStore(session_maker)
        invites = store.get_invite_requests(
            status=status_filter, limit=limit, offset=offset
        )

        return [
            InviteRequestResponse(
                id=invite.id,
                email=invite.email,
                status=invite.status,
                notes=invite.notes,
                created_at=invite.created_at.isoformat(),
                updated_at=invite.updated_at.isoformat(),
            )
            for invite in invites
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            'Error retrieving invite requests',
            extra={'error': str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to retrieve invite requests',
        )


@invite_router.patch('/requests/{email}')
async def update_invite_status(
    request: Request, email: str, update_data: InviteRequestStatusUpdate
):
    """
    Update the status of an invite request (admin only endpoint).

    Args:
        request: The FastAPI request object
        email: Email address of the invite request
        update_data: Status update data

    Returns:
        Success message
    """
    try:
        # Verify user is authenticated
        user_auth: SaasUserAuth = await get_user_auth(request)
        user_id = await user_auth.get_user_id()

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication required',
            )

        # TODO: Add admin role check here when role-based access control is implemented

        # Validate status
        if update_data.status not in ['pending', 'approved', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid status. Must be one of: pending, approved, rejected',
            )

        store = InviteRequestStore(session_maker)
        success = store.update_invite_status(
            email=email.lower(), status=update_data.status, notes=update_data.notes
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Invite request not found',
            )

        logger.info(
            'Invite request status updated',
            extra={'email': email, 'status': update_data.status, 'user_id': user_id},
        )

        return {
            'message': f'Invite request status updated to {update_data.status}',
            'email': email,
            'status': update_data.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            'Error updating invite request status',
            extra={'email': email, 'error': str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to update invite request status',
        )


@invite_router.get('/requests/count')
async def get_invite_requests_count(
    request: Request, status_filter: Optional[str] = None
):
    """
    Get the count of invite requests (admin only endpoint).

    Args:
        request: The FastAPI request object
        status_filter: Optional status filter (pending, approved, rejected)

    Returns:
        Count of invite requests
    """
    try:
        # Verify user is authenticated
        user_auth: SaasUserAuth = await get_user_auth(request)
        user_id = await user_auth.get_user_id()

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication required',
            )

        # TODO: Add admin role check here when role-based access control is implemented

        store = InviteRequestStore(session_maker)
        count = store.count_invite_requests(status=status_filter)

        return {'count': count, 'status': status_filter}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            'Error counting invite requests',
            extra={'error': str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to count invite requests',
        )
