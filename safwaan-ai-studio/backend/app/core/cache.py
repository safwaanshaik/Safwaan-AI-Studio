"""
SAFWAAN AI STUDIO - Caching System
Enterprise-grade Redis-based caching with fallback mechanisms.

This module provides:
- Redis connection management
- Multi-level caching (memory + Redis)
- Cache key management and invalidation
- Performance monitoring
- Fallback to in-memory cache
- TTL-based expiration
"""

import json
import logging
import asyncio
from typing import Any, Optional, Dict, List, Union
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None

# In-memory cache as fallback
_memory_cache: Dict[str, Dict[str, Any]] = {}


class CacheManager:
    """Central cache management class."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = True

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            if _redis_pool is None:
                _redis_pool = ConnectionPool.from_url(
                    settings.REDIS_CACHE_URL,
                    decode_responses=True,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    health_check_interval=30
                )

            self.redis_client = redis.Redis(connection_pool=_redis_pool)

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache connection established")

        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache: {e}")
            self.use_redis = False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    logger.debug(f"Cache hit for key: {key}")
                    return json.loads(value)
            else:
                # Fallback to memory cache
                if key in _memory_cache:
                    entry = _memory_cache[key]
                    if entry['expires'] > asyncio.get_event_loop().time():
                        logger.debug(f"Memory cache hit for key: {key}")
                        return entry['value']
                    else:
                        # Expired, remove it
                        del _memory_cache[key]

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")

        logger.debug(f"Cache miss for key: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized_value = json.dumps(value)

            if self.use_redis and self.redis_client:
                await self.redis_client.set(key, serialized_value, ex=ttl)
                logger.debug(f"Cached value for key: {key} (TTL: {ttl})")
                return True
            else:
                # Fallback to memory cache
                expires = asyncio.get_event_loop().time() + (ttl or 300)
                _memory_cache[key] = {
                    'value': value,
                    'expires': expires
                }
                logger.debug(f"Memory cached value for key: {key} (TTL: {ttl})")
                return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
                logger.debug(f"Deleted cache key: {key}")
                return True
            else:
                # Memory cache
                if key in _memory_cache:
                    del _memory_cache[key]
                    logger.debug(f"Deleted memory cache key: {key}")
                    return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")

        return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                return bool(await self.redis_client.exists(key))
            else:
                return key in _memory_cache

        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                return bool(await self.redis_client.expire(key, ttl))
            else:
                # Memory cache
                if key in _memory_cache:
                    _memory_cache[key]['expires'] = asyncio.get_event_loop().time() + ttl
                    return True

        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")

        return False

    async def ttl(self, key: str) -> int:
        """
        Get time to live for key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if key doesn't exist or error
        """
        try:
            if self.use_redis and self.redis_client:
                return await self.redis_client.ttl(key)
            else:
                # Memory cache
                if key in _memory_cache:
                    expires = _memory_cache[key]['expires']
                    current_time = asyncio.get_event_loop().time()
                    return max(0, int(expires - current_time))
                return -1

        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            if self.use_redis and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    return await self.redis_client.delete(*keys)
                return 0
            else:
                # Memory cache - simple implementation
                deleted = 0
                keys_to_delete = [k for k in _memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del _memory_cache[key]
                    deleted += 1
                return deleted

        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = {
                "cache_type": "redis" if self.use_redis else "memory",
                "connected": self.redis_client is not None if self.use_redis else True,
            }

            if self.use_redis and self.redis_client:
                info = await self.redis_client.info()
                stats.update({
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_connections_received": info.get("total_connections_received", 0),
                })
            else:
                stats.update({
                    "cached_items": len(_memory_cache),
                })

            return stats

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    return await cache_manager.get(key)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    return await cache_manager.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    return await cache_manager.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    return await cache_manager.exists(key)


# Cache key generators
def make_user_cache_key(user_id: str, key_type: str = "data") -> str:
    """Generate cache key for user data."""
    return f"user:{user_id}:{key_type}"


def make_project_cache_key(project_id: str, key_type: str = "data") -> str:
    """Generate cache key for project data."""
    return f"project:{project_id}:{key_type}"


def make_video_cache_key(video_id: str, key_type: str = "data") -> str:
    """Generate cache key for video data."""
    return f"video:{video_id}:{key_type}"


def make_analytics_cache_key(user_id: str, metric: str) -> str:
    """Generate cache key for analytics data."""
    return f"analytics:{user_id}:{metric}"


# Cache decorators
def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args if arg is not None)
            key_parts.extend(f"{k}:{v}" for k, v in kwargs.items() if v is not None)
            cache_key = ":".join(key_parts)

            # Try to get from cache first
            cached_result = await cache_get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            if result is not None:
                await cache_set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


async def init_cache() -> None:
    """Initialize cache system."""
    await cache_manager.connect()
    logger.info("Cache system initialized")


async def close_cache() -> None:
    """Close cache connections."""
    await cache_manager.disconnect()
    logger.info("Cache connections closed")


# Export commonly used functions and classes
__all__ = [
    "CacheManager",
    "cache_manager",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cache_exists",
    "make_user_cache_key",
    "make_project_cache_key",
    "make_video_cache_key",
    "make_analytics_cache_key",
    "cached",
    "init_cache",
    "close_cache",
]