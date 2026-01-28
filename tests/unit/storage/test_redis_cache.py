"""Tests for Redis cache manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openhands.storage.redis_cache import RedisCacheManager


@pytest.fixture
async def cache_manager():
    """Create a Redis cache manager instance."""
    manager = RedisCacheManager(host='localhost', port=6379, password='test')
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_set_get(cache_manager):
    """Test setting and getting values from cache."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.set.return_value = True
        mock_client.get.return_value = '{"key": "value"}'

        # Test set
        result = await cache_manager.set('test_key', {'key': 'value'})
        assert result is True
        mock_client.set.assert_called_once()

        # Test get
        value = await cache_manager.get('test_key')
        assert value == {'key': 'value'}
        mock_client.get.assert_called_once_with('test_key')


@pytest.mark.asyncio
async def test_set_with_ttl(cache_manager):
    """Test setting value with TTL."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.setex.return_value = True

        result = await cache_manager.set('test_key', 'value', ttl=300)
        assert result is True
        mock_client.setex.assert_called_once()


@pytest.mark.asyncio
async def test_delete(cache_manager):
    """Test deleting a key from cache."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.delete.return_value = 1

        result = await cache_manager.delete('test_key')
        assert result is True
        mock_client.delete.assert_called_once_with('test_key')


@pytest.mark.asyncio
async def test_rate_limit(cache_manager):
    """Test rate limiting functionality."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        # First request - no existing counter
        mock_client.get.return_value = None
        mock_client.setex.return_value = True

        allowed, remaining = await cache_manager.rate_limit('user:123', 10, 60)
        assert allowed is True
        assert remaining == 9

        # Second request - existing counter
        mock_client.get.return_value = '5'
        mock_client.incr.return_value = 6

        allowed, remaining = await cache_manager.rate_limit('user:123', 10, 60)
        assert allowed is True
        assert remaining == 4


@pytest.mark.asyncio
async def test_rate_limit_exceeded(cache_manager):
    """Test rate limiting when limit is exceeded."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = '10'

        allowed, remaining = await cache_manager.rate_limit('user:123', 10, 60)
        assert allowed is False
        assert remaining == 0


@pytest.mark.asyncio
async def test_acquire_release_lock(cache_manager):
    """Test distributed lock acquisition and release."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        # Test acquire lock
        mock_client.set.return_value = True
        acquired = await cache_manager.acquire_lock('lock:resource', ttl=30)
        assert acquired is True

        # Test release lock
        mock_client.delete.return_value = 1
        released = await cache_manager.release_lock('lock:resource')
        assert released is True


@pytest.mark.asyncio
async def test_queue_operations(cache_manager):
    """Test queue push and pop operations."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        # Test push to queue
        mock_client.rpush.return_value = 1
        result = await cache_manager.push_to_queue('task_queue', {'task': 'data'})
        assert result is True

        # Test pop from queue
        mock_client.lpop.return_value = '{"task": "data"}'
        item = await cache_manager.pop_from_queue('task_queue')
        assert item == {'task': 'data'}


@pytest.mark.asyncio
async def test_get_queue_length(cache_manager):
    """Test getting queue length."""
    with patch.object(cache_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.llen.return_value = 5

        length = await cache_manager.get_queue_length('task_queue')
        assert length == 5
