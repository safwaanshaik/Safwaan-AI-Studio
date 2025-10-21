"""
SAFWAAN AI STUDIO - Custom Exceptions
Enterprise-grade custom exceptions for comprehensive error handling.

This module provides:
- Base exception classes with proper error codes
- Specific exceptions for different domains (auth, API, AI, etc.)
- Error response formatting
- Exception handling utilities
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException


class SafwaanAIException(Exception):
    """Base exception class for Safwaan AI Studio."""

    def __init__(
        self,
        detail: str,
        status_code: int = 500,
        error_type: str = "internal_error",
        headers: Optional[Dict[str, str]] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        self.headers = headers or {}
        super().__init__(self.detail)


class AuthenticationError(SafwaanAIException):
    """Exception raised for authentication failures."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            status_code=401,
            error_type="authentication_error",
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(SafwaanAIException):
    """Exception raised for authorization failures."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            detail=detail,
            status_code=403,
            error_type="authorization_error"
        )


class ValidationError(SafwaanAIException):
    """Exception raised for validation failures."""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_type="validation_error"
        )


class NotFoundError(SafwaanAIException):
    """Exception raised when a resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            detail=detail,
            status_code=404,
            error_type="not_found_error"
        )


class ConflictError(SafwaanAIException):
    """Exception raised for resource conflicts."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            detail=detail,
            status_code=409,
            error_type="conflict_error"
        )


class RateLimitError(SafwaanAIException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            detail=detail,
            status_code=429,
            error_type="rate_limit_error",
            headers={"Retry-After": str(retry_after)}
        )
        self.retry_after = retry_after


class ServiceUnavailableError(SafwaanAIException):
    """Exception raised when a service is unavailable."""

    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            detail=detail,
            status_code=503,
            error_type="service_unavailable_error"
        )


class ExternalServiceError(SafwaanAIException):
    """Exception raised when an external service fails."""

    def __init__(self, detail: str = "External service error", service: str = "unknown"):
        super().__init__(
            detail=f"{service}: {detail}",
            status_code=502,
            error_type="external_service_error"
        )
        self.service = service


# AI Engine specific exceptions
class AIEngineError(SafwaanAIException):
    """Base exception for AI engine errors."""

    def __init__(self, detail: str = "AI engine error"):
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="ai_engine_error"
        )


class ModelNotAvailableError(AIEngineError):
    """Exception raised when an AI model is not available."""

    def __init__(self, model: str):
        super().__init__(detail=f"Model '{model}' is not available")
        self.model = model


class GenerationFailedError(AIEngineError):
    """Exception raised when video generation fails."""

    def __init__(self, detail: str = "Video generation failed"):
        super().__init__(detail=detail)


class InsufficientCreditsError(SafwaanAIException):
    """Exception raised when user has insufficient credits."""

    def __init__(self, required: int, available: int):
        super().__init__(
            detail=f"Insufficient credits. Required: {required}, Available: {available}",
            status_code=402,
            error_type="insufficient_credits_error"
        )
        self.required = required
        self.available = available


class SubscriptionExpiredError(SafwaanAIException):
    """Exception raised when user subscription has expired."""

    def __init__(self, detail: str = "Subscription has expired"):
        super().__init__(
            detail=detail,
            status_code=402,
            error_type="subscription_expired_error"
        )


class FileUploadError(SafwaanAIException):
    """Exception raised for file upload failures."""

    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            detail=detail,
            status_code=400,
            error_type="file_upload_error"
        )


class FileTooLargeError(FileUploadError):
    """Exception raised when uploaded file is too large."""

    def __init__(self, max_size: int, actual_size: int):
        super().__init__(
            detail=f"File too large. Maximum size: {max_size} bytes, Actual size: {actual_size} bytes"
        )
        self.max_size = max_size
        self.actual_size = actual_size


class UnsupportedFileTypeError(FileUploadError):
    """Exception raised when uploaded file type is not supported."""

    def __init__(self, file_type: str, supported_types: list):
        super().__init__(
            detail=f"Unsupported file type '{file_type}'. Supported types: {', '.join(supported_types)}"
        )
        self.file_type = file_type
        self.supported_types = supported_types


# Database specific exceptions
class DatabaseError(SafwaanAIException):
    """Exception raised for database operation failures."""

    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="database_error"
        )


class ConnectionError(DatabaseError):
    """Exception raised for database connection failures."""

    def __init__(self, detail: str = "Database connection failed"):
        super().__init__(detail=detail)


# Cache specific exceptions
class CacheError(SafwaanAIException):
    """Exception raised for cache operation failures."""

    def __init__(self, detail: str = "Cache operation failed"):
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="cache_error"
        )


# Social platform specific exceptions
class SocialPlatformError(SafwaanAIException):
    """Base exception for social platform errors."""

    def __init__(self, platform: str, detail: str = "Social platform error"):
        super().__init__(
            detail=f"{platform}: {detail}",
            status_code=502,
            error_type="social_platform_error"
        )
        self.platform = platform


class YouTubeError(SocialPlatformError):
    """Exception raised for YouTube API errors."""

    def __init__(self, detail: str = "YouTube API error"):
        super().__init__(platform="YouTube", detail=detail)


class TikTokError(SocialPlatformError):
    """Exception raised for TikTok API errors."""

    def __init__(self, detail: str = "TikTok API error"):
        super().__init__(platform="TikTok", detail=detail)


class InstagramError(SocialPlatformError):
    """Exception raised for Instagram API errors."""

    def __init__(self, detail: str = "Instagram API error"):
        super().__init__(platform="Instagram", detail=detail)


# Billing specific exceptions
class BillingError(SafwaanAIException):
    """Base exception for billing errors."""

    def __init__(self, detail: str = "Billing operation failed"):
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="billing_error"
        )


class PaymentFailedError(BillingError):
    """Exception raised when payment processing fails."""

    def __init__(self, detail: str = "Payment processing failed"):
        super().__init__(detail=detail)


class RefundFailedError(BillingError):
    """Exception raised when refund processing fails."""

    def __init__(self, detail: str = "Refund processing failed"):
        super().__init__(detail=detail)


# Utility functions
def create_error_response(exception: SafwaanAIException) -> Dict[str, Any]:
    """Create standardized error response from exception."""
    return {
        "error": exception.detail,
        "type": exception.error_type,
        "status_code": exception.status_code
    }


def handle_exception(exception: Exception) -> SafwaanAIException:
    """Convert standard exceptions to SafwaanAI exceptions."""
    if isinstance(exception, SafwaanAIException):
        return exception

    # Handle common Python exceptions
    if isinstance(exception, ValueError):
        return ValidationError(str(exception))
    elif isinstance(exception, KeyError):
        return NotFoundError("Required field missing")
    elif isinstance(exception, PermissionError):
        return AuthorizationError("Permission denied")
    elif isinstance(exception, ConnectionError):
        return ServiceUnavailableError("Connection failed")
    else:
        return SafwaanAIException(f"Unexpected error: {str(exception)}")


# Export all exception classes
__all__ = [
    "SafwaanAIException",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServiceUnavailableError",
    "ExternalServiceError",
    "AIEngineError",
    "ModelNotAvailableError",
    "GenerationFailedError",
    "InsufficientCreditsError",
    "SubscriptionExpiredError",
    "FileUploadError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "DatabaseError",
    "ConnectionError",
    "CacheError",
    "SocialPlatformError",
    "YouTubeError",
    "TikTokError",
    "InstagramError",
    "BillingError",
    "PaymentFailedError",
    "RefundFailedError",
    "create_error_response",
    "handle_exception",
]