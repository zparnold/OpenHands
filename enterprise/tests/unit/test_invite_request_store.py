"""Unit tests for invite request store."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from storage.invite_request import InviteRequest
from storage.invite_request_store import InviteRequestStore


@pytest.fixture
def mock_session_maker():
    """Create a mock session maker."""
    session = MagicMock()
    session_maker = MagicMock()
    session_maker.return_value.__enter__.return_value = session
    session_maker.return_value.__exit__.return_value = None
    return session_maker, session


def test_create_invite_request_success(mock_session_maker):
    """Test successful creation of invite request."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query to return no existing invite
    session.query.return_value.filter.return_value.first.return_value = None

    result = store.create_invite_request('test@example.com', 'Test notes')

    assert result is True
    session.add.assert_called_once()
    session.commit.assert_called_once()


def test_create_invite_request_duplicate(mock_session_maker):
    """Test creation with duplicate email."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query to return existing invite
    existing_invite = InviteRequest(
        id=1,
        email='test@example.com',
        status='pending',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.query.return_value.filter.return_value.first.return_value = existing_invite

    result = store.create_invite_request('test@example.com', 'Test notes')

    assert result is False
    session.add.assert_not_called()


def test_get_invite_requests_with_filter(mock_session_maker):
    """Test getting invite requests with status filter."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query result
    mock_invites = [
        InviteRequest(
            id=1,
            email='test1@example.com',
            status='pending',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        InviteRequest(
            id=2,
            email='test2@example.com',
            status='pending',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    query_mock = session.query.return_value
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.all.return_value = mock_invites

    result = store.get_invite_requests(status='pending', limit=10, offset=0)

    assert len(result) == 2
    assert result[0].email == 'test1@example.com'
    assert result[1].email == 'test2@example.com'


def test_update_invite_status_success(mock_session_maker):
    """Test successful update of invite status."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock existing invite
    existing_invite = InviteRequest(
        id=1,
        email='test@example.com',
        status='pending',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.query.return_value.filter.return_value.first.return_value = existing_invite

    result = store.update_invite_status('test@example.com', 'approved')

    assert result is True
    assert existing_invite.status == 'approved'
    session.commit.assert_called_once()


def test_update_invite_status_not_found(mock_session_maker):
    """Test update when invite not found."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query to return None
    session.query.return_value.filter.return_value.first.return_value = None

    result = store.update_invite_status('test@example.com', 'approved')

    assert result is False
    session.commit.assert_not_called()


def test_get_invite_request_by_email(mock_session_maker):
    """Test getting invite request by email."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock existing invite
    existing_invite = InviteRequest(
        id=1,
        email='test@example.com',
        status='pending',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.query.return_value.filter.return_value.first.return_value = existing_invite

    result = store.get_invite_request_by_email('test@example.com')

    assert result is not None
    assert result.email == 'test@example.com'
    assert result.status == 'pending'


def test_count_invite_requests(mock_session_maker):
    """Test counting invite requests."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock count result
    query_mock = session.query.return_value
    query_mock.filter.return_value = query_mock
    query_mock.count.return_value = 5

    result = store.count_invite_requests(status='pending')

    assert result == 5


def test_create_invite_request_lowercase_email(mock_session_maker):
    """Test that email is converted to lowercase."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query to return no existing invite
    session.query.return_value.filter.return_value.first.return_value = None

    result = store.create_invite_request('Test@Example.COM', 'Test notes')

    assert result is True
    # Verify the email was lowercased when added
    call_args = session.add.call_args[0][0]
    assert call_args.email == 'test@example.com'


def test_create_invite_request_exception_handling(mock_session_maker):
    """Test exception handling in create_invite_request."""
    session_maker, session = mock_session_maker
    store = InviteRequestStore(session_maker)

    # Mock query to raise an exception
    session.query.side_effect = Exception('Database error')

    result = store.create_invite_request('test@example.com', 'Test notes')

    assert result is False
