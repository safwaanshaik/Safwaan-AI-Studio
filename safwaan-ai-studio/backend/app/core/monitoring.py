"""
SAFWAAN AI STUDIO - Monitoring and Observability
Enterprise-grade monitoring with Prometheus metrics and health checks.

This module provides:
- Prometheus metrics collection
- Health check endpoints
- Performance monitoring
- Error tracking and alerting
- System resource monitoring
- Business metrics tracking
"""

import logging
import time
import psutil
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import prometheus_client as prom
from prometheus_client import Counter, Gauge, Histogram, Summary

from app.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
# HTTP request metrics
http_requests_total = Counter(
    'safwaan_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration = Histogram(
    'safwaan_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Database metrics
db_connections_active = Gauge(
    'safwaan_db_connections_active',
    'Number of active database connections'
)

db_query_duration = Histogram(
    'safwaan_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# Cache metrics
cache_hits_total = Counter(
    'safwaan_cache_hits_total',
    'Total number of cache hits'
)

cache_misses_total = Counter(
    'safwaan_cache_misses_total',
    'Total number of cache misses'
)

# AI Engine metrics
ai_requests_total = Counter(
    'safwaan_ai_requests_total',
    'Total number of AI generation requests',
    ['model', 'status']
)

ai_generation_duration = Histogram(
    'safwaan_ai_generation_duration_seconds',
    'AI generation duration in seconds',
    ['model']
)

# Business metrics
videos_generated_total = Counter(
    'safwaan_videos_generated_total',
    'Total number of videos generated'
)

users_active = Gauge(
    'safwaan_users_active',
    'Number of active users'
)

revenue_total = Counter(
    'safwaan_revenue_total',
    'Total revenue generated',
    ['currency']
)

# System metrics
cpu_usage = Gauge(
    'safwaan_cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage = Gauge(
    'safwaan_memory_usage_bytes',
    'Memory usage in bytes'
)

disk_usage = Gauge(
    'safwaan_disk_usage_bytes',
    'Disk usage in bytes',
    ['mount_point']
)

# Error metrics
errors_total = Counter(
    'safwaan_errors_total',
    'Total number of errors',
    ['type', 'component']
)


class MonitoringManager:
    """Central monitoring management class."""

    def __init__(self):
        self.metrics_enabled = True
        self.system_monitoring_enabled = True

    async def start_system_monitoring(self) -> None:
        """Start system resource monitoring."""
        if not self.system_monitoring_enabled:
            return

        logger.info("Starting system monitoring")

        # Update system metrics every 30 seconds
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage.set(cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                memory_usage.set(memory.used)

                # Disk usage
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_usage.labels(mount_point=partition.mountpoint).set(usage.used)
                    except Exception:
                        pass  # Skip inaccessible partitions

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(30)

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float
    ) -> None:
        """Record HTTP request metrics."""
        if not self.metrics_enabled:
            return

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()

        http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def record_db_query(self, operation: str, duration: float) -> None:
        """Record database query metrics."""
        if not self.metrics_enabled:
            return

        db_query_duration.labels(operation=operation).observe(duration)

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        if not self.metrics_enabled:
            return

        cache_hits_total.inc()

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        if not self.metrics_enabled:
            return

        cache_misses_total.inc()

    def record_ai_request(
        self,
        model: str,
        status: str,
        duration: Optional[float] = None
    ) -> None:
        """Record AI request metrics."""
        if not self.metrics_enabled:
            return

        ai_requests_total.labels(model=model, status=status).inc()

        if duration is not None:
            ai_generation_duration.labels(model=model).observe(duration)

    def record_video_generated(self) -> None:
        """Record video generation."""
        if not self.metrics_enabled:
            return

        videos_generated_total.inc()

    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics."""
        if not self.metrics_enabled:
            return

        errors_total.labels(type=error_type, component=component).inc()

    def update_active_users(self, count: int) -> None:
        """Update active users count."""
        if not self.metrics_enabled:
            return

        users_active.set(count)

    def record_revenue(self, amount: float, currency: str = "USD") -> None:
        """Record revenue metrics."""
        if not self.metrics_enabled:
            return

        revenue_total.labels(currency=currency).inc(amount)

    def get_metrics(self) -> str:
        """Get current metrics in Prometheus format."""
        return prom.generate_latest().decode('utf-8')

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary with health check results
        """
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {}
        }

        # System health
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            health_status["checks"]["system"] = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "status": "healthy" if cpu_percent < 90 and memory.percent < 90 else "warning"
            }
        except Exception as e:
            health_status["checks"]["system"] = {
                "status": "error",
                "error": str(e)
            }

        # Database health (placeholder - implement actual check)
        health_status["checks"]["database"] = {
            "status": "healthy",  # TODO: Implement actual DB health check
            "connections": "unknown"
        }

        # Redis health (placeholder - implement actual check)
        health_status["checks"]["redis"] = {
            "status": "healthy",  # TODO: Implement actual Redis health check
        }

        # AI Engine health (placeholder - implement actual check)
        health_status["checks"]["ai_engine"] = {
            "status": "healthy",  # TODO: Implement actual AI engine health check
        }

        # Overall status
        unhealthy_checks = [
            check for check in health_status["checks"].values()
            if check.get("status") in ["error", "unhealthy"]
        ]

        if unhealthy_checks:
            health_status["status"] = "unhealthy"

        return health_status


# Global monitoring manager instance
monitoring_manager = MonitoringManager()


# Convenience functions
def record_http_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record HTTP request metrics."""
    monitoring_manager.record_http_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, duration: float) -> None:
    """Record database query metrics."""
    monitoring_manager.record_db_query(operation, duration)


def record_cache_hit() -> None:
    """Record cache hit."""
    monitoring_manager.record_cache_hit()


def record_cache_miss() -> None:
    """Record cache miss."""
    monitoring_manager.record_cache_miss()


def record_ai_request(model: str, status: str, duration: Optional[float] = None) -> None:
    """Record AI request metrics."""
    monitoring_manager.record_ai_request(model, status, duration)


def record_video_generated() -> None:
    """Record video generation."""
    monitoring_manager.record_video_generated()


def record_error(error_type: str, component: str) -> None:
    """Record error metrics."""
    monitoring_manager.record_error(error_type, component)


def update_active_users(count: int) -> None:
    """Update active users count."""
    monitoring_manager.update_active_users(count)


def record_revenue(amount: float, currency: str = "USD") -> None:
    """Record revenue metrics."""
    monitoring_manager.record_revenue(amount, currency)


# Monitoring decorators
def monitor_http_request():
    """Decorator to monitor HTTP requests."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            # Extract request info from args (FastAPI dependency injection)
            request = None
            for arg in args:
                if hasattr(arg, 'method') and hasattr(arg, 'url'):
                    request = arg
                    break

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                if request and hasattr(result, 'status_code'):
                    record_http_request(
                        request.method,
                        str(request.url.path),
                        result.status_code,
                        duration
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time
                record_error("exception", func.__name__)
                raise

        return wrapper
    return decorator


def monitor_db_query(operation: str):
    """Decorator to monitor database queries."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                record_db_query(operation, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                record_db_query(operation, duration)
                record_error("db_error", operation)
                raise
        return wrapper
    return decorator


async def init_monitoring() -> None:
    """Initialize monitoring system."""
    logger.info("Monitoring system initialized")

    # Start system monitoring in background
    asyncio.create_task(monitoring_manager.start_system_monitoring())


# Export commonly used functions and classes
__all__ = [
    "MonitoringManager",
    "monitoring_manager",
    "record_http_request",
    "record_db_query",
    "record_cache_hit",
    "record_cache_miss",
    "record_ai_request",
    "record_video_generated",
    "record_error",
    "update_active_users",
    "record_revenue",
    "monitor_http_request",
    "monitor_db_query",
    "init_monitoring",
]