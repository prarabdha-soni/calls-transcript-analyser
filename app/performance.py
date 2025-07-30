"""
Performance optimization module for the Sales Call Analytics API
Includes caching, connection pooling, and query optimization.
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-based cache manager for API responses"""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        self.redis_client = None
        self.default_ttl = 300  # 5 minutes

    async def __aenter__(self):
        self.redis_client = redis.from_url(self.redis_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.redis_client:
            await self.redis_client.close()

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters"""
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None

    async def set(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    key, ttl or self.default_ttl, json.dumps(value)
                )
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
        return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    return await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache delete error: {e}")
        return 0


class ConnectionPoolManager:
    """Database connection pool manager"""

    def __init__(self) -> None:
        self.pool = None

    async def initialize_pool(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
    ) -> None:
        """Initialize connection pool with optimized settings"""
        from sqlalchemy.ext.asyncio import create_async_engine

        self.pool = create_async_engine(
            database_url,
            echo=False,  # Disable SQL logging for performance
            future=True,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections every hour
        )

    @asynccontextmanager
    async def get_session(self):
        """Get database session from pool"""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")

        from app.database import AsyncSessionLocal

        async_session = AsyncSessionLocal()
        try:
            yield async_session
        finally:
            await async_session.close()


class QueryOptimizer:
    """Query optimization utilities"""

    @staticmethod
    async def optimize_calls_query(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        agent_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Optimized calls query with proper indexing and pagination"""

        # Build query with proper joins and conditions
        query = """
        SELECT 
            c.call_id, c.agent_id, c.customer_id, c.language,
            c.start_time, c.duration_seconds, c.transcript,
            c.agent_talk_ratio, c.customer_sentiment_score
        FROM calls c
        WHERE 1=1
        """

        params: Dict[str, Any] = {}

        if agent_id:
            query += " AND c.agent_id = :agent_id"
            params["agent_id"] = agent_id

        if from_date:
            query += " AND c.start_time >= :from_date"
            params["from_date"] = from_date

        if to_date:
            query += " AND c.start_time <= :to_date"
            params["to_date"] = to_date

        if min_sentiment is not None:
            query += " AND c.customer_sentiment_score >= :min_sentiment"
            params["min_sentiment"] = min_sentiment

        if max_sentiment is not None:
            query += " AND c.customer_sentiment_score <= :max_sentiment"
            params["max_sentiment"] = max_sentiment

        # Add ordering and pagination
        query += " ORDER BY c.start_time DESC"
        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        # Execute query
        result = await session.execute(text(query), params)
        calls = result.fetchall()

        # Get total count for pagination
        count_query = """
        SELECT COUNT(*) as total
        FROM calls c
        WHERE 1=1
        """

        count_params: Dict[str, Any] = {}

        if count_params:
            count_query += " AND " + " AND ".join(
                f"c.{k.replace('_', '')} = :{k}" for k in count_params.keys()
            )

        count_result = await session.execute(text(count_query), count_params)
        total = count_result.scalar()

        return {
            "calls": [dict(call) for call in calls],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    async def optimize_analytics_query(session: AsyncSession) -> List[Dict[str, Any]]:
        """Optimized analytics query with aggregation"""

        query = """
        SELECT 
            agent_id,
            COUNT(*) as total_calls,
            AVG(customer_sentiment_score) as avg_sentiment,
            AVG(agent_talk_ratio) as avg_talk_ratio
        FROM calls
        GROUP BY agent_id
        ORDER BY total_calls DESC, avg_sentiment DESC
        """

        result = await session.execute(text(query))
        analytics = result.fetchall()

        return [dict(analytic) for analytic in analytics]


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""

    def __init__(self) -> None:
        self.metrics = {
            "api_calls": {},
            "query_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
        }

    def record_api_call(
        self, endpoint: str, method: str, duration: float, status_code: int = 200
    ) -> None:
        """Record API call metrics"""
        key = f"{method}_{endpoint}"
        if key not in self.metrics["api_calls"]:
            self.metrics["api_calls"][key] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "status_codes": {},
            }

        metric = self.metrics["api_calls"][key]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["avg_time"] = metric["total_time"] / metric["count"]
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)

        status_str = str(status_code)
        metric["status_codes"][status_str] = (
            metric["status_codes"].get(status_str, 0) + 1
        )

    def record_query_time(self, query_type: str, duration: float) -> None:
        """Record database query metrics"""
        if query_type not in self.metrics["query_times"]:
            self.metrics["query_times"][query_type] = []
        self.metrics["query_times"][query_type].append(duration)

    def record_cache_hit(self) -> None:
        """Record cache hit"""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self) -> None:
        """Record cache miss"""
        self.metrics["cache_misses"] += 1

    def record_error(self, error_type: str) -> None:
        """Record error"""
        self.metrics["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        return self.metrics["cache_hits"] / total if total > 0 else 0


# Global instances
cache_manager = CacheManager()
pool_manager = ConnectionPoolManager()
query_optimizer = QueryOptimizer()
performance_monitor = PerformanceMonitor()


def cache_response(ttl: int = 300):
    """Decorator to cache API responses"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"api:{func.__name__}:{hash(args_str)}"

            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                performance_monitor.record_cache_hit()
                return cached_result

            performance_monitor.record_cache_miss()

            # Execute function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Cache the result
                await cache_manager.set(cache_key, result, ttl)

                return result
            except Exception as e:
                performance_monitor.record_error("api_error")
                raise

        return wrapper

    return decorator


def monitor_performance(func):
    """Decorator to monitor function performance"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            # Record metrics based on function name
            if "calls" in func.__name__:
                performance_monitor.record_query_time("calls_query", duration)
            elif "analytics" in func.__name__:
                performance_monitor.record_query_time("analytics_query", duration)

            return result
        except Exception as e:
            performance_monitor.record_error("query_error")
            raise

    return wrapper
