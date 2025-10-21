"""
SAFWAAN AI STUDIO - Logging Configuration
Enterprise-grade structured logging with JSON format and multiple handlers.

This module provides:
- Structured JSON logging for production
- Console logging for development
- File logging with rotation
- Request ID tracking
- Performance monitoring
- Security event logging
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger


class RequestIDFilter(logging.Filter):
    """Filter to add request ID to log records."""

    def filter(self, record):
        # Try to get request ID from thread-local or context
        record.request_id = getattr(record, 'request_id', 'unknown')
        return True


class SafwaanFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for Safwaan AI Studio."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add custom fields
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['version'] = '5.0.0'

        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id

        # Add additional context
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('json' or 'text')
        log_file: Path to log file (optional)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """

    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Create formatters
    if format_type == "json":
        formatter = SafwaanFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())

    # Add console handler to root logger
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIDFilter())

        root_logger.addHandler(file_handler)

    # Setup specific loggers for different components
    setup_component_loggers(numeric_level, formatter)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized", extra={
        "level": level,
        "format": format_type,
        "log_file": log_file or "console_only"
    })


def setup_component_loggers(level: int, formatter: logging.Formatter) -> None:
    """Setup specialized loggers for different application components."""

    # AI Engine Logger
    ai_logger = logging.getLogger('safwaan.ai_engine')
    ai_logger.setLevel(level)

    # Database Logger
    db_logger = logging.getLogger('safwaan.database')
    db_logger.setLevel(level)

    # Security Logger (always INFO and above)
    security_logger = logging.getLogger('safwaan.security')
    security_logger.setLevel(logging.INFO)

    # API Logger
    api_logger = logging.getLogger('safwaan.api')
    api_logger.setLevel(level)

    # Worker Logger
    worker_logger = logging.getLogger('safwaan.worker')
    worker_logger.setLevel(level)

    # Analytics Logger
    analytics_logger = logging.getLogger('safwaan.analytics')
    analytics_logger.setLevel(level)

    # Billing Logger
    billing_logger = logging.getLogger('safwaan.billing')
    billing_logger.setLevel(level)


class LoggerMixin:
    """Mixin class to add logging capabilities to classes."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)


def log_request_middleware(request, response, request_id: str = None) -> None:
    """
    Log HTTP request/response details.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        request_id: Request ID for tracking
    """
    logger = logging.getLogger('safwaan.api.request')

    # Extract request details
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request_id,
    }

    # Extract response details
    response_info = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "request_id": request_id,
    }

    # Remove sensitive headers
    sensitive_headers = ["authorization", "x-api-key", "cookie"]
    for header in sensitive_headers:
        if header in request_info["headers"]:
            request_info["headers"][header] = "***"

    logger.info("HTTP Request", extra={
        "request": request_info,
        "response": response_info,
        "duration_ms": getattr(response, 'duration', None)
    })


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Log security-related events.

    Args:
        event_type: Type of security event
        user_id: User ID associated with event
        details: Additional event details
        request_id: Request ID for tracking
    """
    logger = logging.getLogger('safwaan.security')

    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "details": details or {},
        "request_id": request_id,
    }

    if event_type in ["login_failure", "suspicious_activity", "rate_limit_exceeded"]:
        logger.warning("Security Event", extra=log_data)
    else:
        logger.info("Security Event", extra=log_data)


def log_performance_metric(
    operation: str,
    duration_ms: float,
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Log performance metrics.

    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        metadata: Additional metadata
        request_id: Request ID for tracking
    """
    logger = logging.getLogger('safwaan.performance')

    log_data = {
        "operation": operation,
        "duration_ms": duration_ms,
        "metadata": metadata or {},
        "request_id": request_id,
    }

    logger.info("Performance Metric", extra=log_data)


def log_business_event(
    event_type: str,
    user_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Log business-related events for analytics.

    Args:
        event_type: Type of business event
        user_id: User ID associated with event
        data: Event data
        request_id: Request ID for tracking
    """
    logger = logging.getLogger('safwaan.business')

    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "data": data or {},
        "request_id": request_id,
    }

    logger.info("Business Event", extra=log_data)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation: str, logger_name: str = "safwaan.performance"):
        self.operation = operation
        self.logger_name = logger_name
        self.start_time = None
        self.metadata = {}

    def __enter__(self):
        self.start_time = logging.time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (logging.time.time() - self.start_time) * 1000
            logger = logging.getLogger(self.logger_name)
            logger.info(f"Operation completed: {self.operation}", extra={
                "operation": self.operation,
                "duration_ms": duration_ms,
                "metadata": self.metadata
            })

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the performance log."""
        self.metadata[key] = value


# Export commonly used functions and classes
__all__ = [
    "setup_logging",
    "LoggerMixin",
    "log_request_middleware",
    "log_security_event",
    "log_performance_metric",
    "log_business_event",
    "PerformanceTimer",
]