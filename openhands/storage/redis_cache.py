"""Redis cache manager for distributed caching and rate limiting."""

import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Manages Redis connections for caching, rate limiting, and task queues."""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        password: str | None = None,
        db: int = 0,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self._client: Redis | None = None

    async def get_client(self) -> Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
            )
        return self._client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache with optional TTL (time to live in seconds)."""
        try:
            client = await self.get_client()
            serialized_value = json.dumps(value)
            if ttl:
                return await client.setex(key, ttl, serialized_value)
            else:
                return await client.set(key, serialized_value)
        except Exception as e:
            logger.exception(f'Failed to set cache key {key}: {e}')
            return False

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.exception(f'Failed to get cache key {key}: {e}')
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            client = await self.get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.exception(f'Failed to delete cache key {key}: {e}')
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.exception(f'Failed to check existence of cache key {key}: {e}')
            return False

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment a counter in cache."""
        try:
            client = await self.get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.exception(f'Failed to increment cache key {key}: {e}')
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key."""
        try:
            client = await self.get_client()
            return await client.expire(key, ttl)
        except Exception as e:
            logger.exception(f'Failed to set expiry on cache key {key}: {e}')
            return False

    async def rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Implement rate limiting using sliding window counter.

        Returns:
            tuple: (is_allowed, remaining_requests)
        """
        try:
            client = await self.get_client()
            current = await client.get(key)

            if current is None:
                # First request in window
                await client.setex(key, window_seconds, '1')
                return True, max_requests - 1

            current_count = int(current)
            if current_count >= max_requests:
                return False, 0

            new_count = await client.incr(key)
            return True, max_requests - new_count
        except Exception as e:
            logger.exception(f'Failed to apply rate limit for key {key}: {e}')
            # On error, allow the request to avoid blocking
            return True, max_requests

    async def acquire_lock(
        self, lock_key: str, ttl: int = 30, timeout: int = 10
    ) -> bool:
        """
        Acquire a distributed lock.

        Args:
            lock_key: Unique key for the lock
            ttl: Time to live for the lock in seconds
            timeout: Maximum time to wait for lock in seconds

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        try:
            client = await self.get_client()
            # Use SET with NX (only set if not exists) and EX (expiry)
            result = await client.set(lock_key, '1', nx=True, ex=ttl)
            return result is not None
        except Exception as e:
            logger.exception(f'Failed to acquire lock {lock_key}: {e}')
            return False

    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock."""
        try:
            return await self.delete(lock_key)
        except Exception as e:
            logger.exception(f'Failed to release lock {lock_key}: {e}')
            return False

    async def push_to_queue(self, queue_name: str, item: Any) -> bool:
        """Push an item to a queue (list in Redis)."""
        try:
            client = await self.get_client()
            serialized_item = json.dumps(item)
            await client.rpush(queue_name, serialized_item)
            return True
        except Exception as e:
            logger.exception(f'Failed to push to queue {queue_name}: {e}')
            return False

    async def pop_from_queue(self, queue_name: str, timeout: int = 0) -> Any | None:
        """Pop an item from a queue (blocking if timeout > 0)."""
        try:
            client = await self.get_client()
            if timeout > 0:
                result = await client.blpop(queue_name, timeout=timeout)
                if result:
                    _, value = result
                    return json.loads(value)
            else:
                value = await client.lpop(queue_name)
                if value:
                    return json.loads(value)
            return None
        except Exception as e:
            logger.exception(f'Failed to pop from queue {queue_name}: {e}')
            return None

    async def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a queue."""
        try:
            client = await self.get_client()
            return await client.llen(queue_name)
        except Exception as e:
            logger.exception(f'Failed to get queue length for {queue_name}: {e}')
            return 0
