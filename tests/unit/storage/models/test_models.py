"""Tests for database models."""

import pytest
from datetime import datetime, UTC

from openhands.storage.models.user import User
from openhands.storage.models.organization import Organization, OrganizationMembership
from openhands.storage.models.session import Session
from openhands.storage.models.secret import Secret
from pydantic import SecretStr


def test_user_model():
    """Test User model creation and representation."""
    now = datetime.now(UTC)
    user = User(
        id='user123',
        email='test@example.com',
        display_name='Test User',
        created_at=now,
    )

    assert user.id == 'user123'
    assert user.email == 'test@example.com'
    assert user.display_name == 'Test User'
    assert isinstance(user.created_at, datetime)
    assert user.created_at.tzinfo == UTC


def test_organization_model():
    """Test Organization model creation."""
    now = datetime.now(UTC)
    org = Organization(
        id='org123',
        name='Test Organization',
        created_at=now,
    )

    assert org.id == 'org123'
    assert org.name == 'Test Organization'
    assert isinstance(org.created_at, datetime)


def test_organization_membership_model():
    """Test OrganizationMembership model creation."""
    membership = OrganizationMembership(
        id='mem123',
        user_id='user123',
        organization_id='org123',
        role='admin',
    )

    assert membership.id == 'mem123'
    assert membership.user_id == 'user123'
    assert membership.organization_id == 'org123'
    assert membership.role == 'admin'


def test_session_model():
    """Test Session model creation."""
    session = Session(
        id='session123',
        user_id='user123',
        organization_id='org123',
        conversation_id='conv123',
        state={'key': 'value'},
    )

    assert session.id == 'session123'
    assert session.user_id == 'user123'
    assert session.organization_id == 'org123'
    assert session.conversation_id == 'conv123'
    assert session.state == {'key': 'value'}


def test_secret_model():
    """Test Secret model creation."""
    secret = Secret(
        id='secret123',
        user_id='user123',
        key='api_key',
        value=SecretStr('secret_value'),
        description='API key for service',
    )

    assert secret.id == 'secret123'
    assert secret.user_id == 'user123'
    assert secret.key == 'api_key'
    assert isinstance(secret.value, SecretStr)
    assert secret.description == 'API key for service'


def test_organization_secret():
    """Test organization-level secret."""
    secret = Secret(
        id='secret123',
        organization_id='org123',
        key='org_api_key',
        value=SecretStr('secret_value'),
        description='Organization API key',
    )

    assert secret.organization_id == 'org123'
    assert secret.user_id is None
