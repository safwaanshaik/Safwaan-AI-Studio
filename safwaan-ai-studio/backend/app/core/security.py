"""
SAFWAAN AI STUDIO - Security Management
Enterprise-grade security with JWT, OAuth2, RBAC, and encryption.

This module provides:
- JWT token management and validation
- Password hashing with bcrypt
- OAuth2 integration (Google, GitHub, Discord)
- Role-based access control (RBAC)
- API key management
- Data encryption utilities
- Security audit logging
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.utils.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# HTTP Bearer for API keys
http_bearer = HTTPBearer(auto_error=False)


class SecurityManager:
    """Central security management class."""

    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data."""
        if settings.ENCRYPTION_KEY:
            # Use provided key
            key = settings.ENCRYPTION_KEY.encode()
        else:
            # Generate a new key (development only)
            if settings.ENVIRONMENT == "production":
                raise ValueError("ENCRYPTION_KEY must be set in production")
            key = Fernet.generate_key()

        # Ensure key is 32 bytes for Fernet
        if len(key) != 32:
            # Derive key using PBKDF2
            salt = b"safwaan_ai_salt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key))

        return key

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        f = Fernet(self.encryption_key)
        return f.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_data.encode()).decode()


# Global security manager instance
security_manager = SecurityManager()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    credentials_exception = AuthenticationError("Could not validate credentials")

    try:
        payload = verify_token(token)
        if payload is None:
            raise credentials_exception

        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

        # TODO: Fetch user from database
        # For now, return mock user data
        user = {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "subscription_tier": payload.get("tier", "free")
        }

        return user

    except JWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current active user."""
    # TODO: Check if user is active
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current admin user."""
    if current_user.get("role") != "admin":
        raise AuthorizationError("Admin access required")
    return current_user


def check_permissions(
    user: Dict[str, Any],
    required_permissions: List[str]
) -> bool:
    """Check if user has required permissions."""
    user_role = user.get("role", "user")
    user_permissions = get_role_permissions(user_role)

    return all(perm in user_permissions for perm in required_permissions)


def get_role_permissions(role: str) -> List[str]:
    """Get permissions for a role."""
    role_permissions = {
        "admin": [
            "users:read", "users:write", "users:delete",
            "projects:read", "projects:write", "projects:delete",
            "videos:read", "videos:write", "videos:delete",
            "analytics:read", "analytics:write",
            "billing:read", "billing:write",
            "system:read", "system:write"
        ],
        "pro": [
            "users:read", "users:write",
            "projects:read", "projects:write", "projects:delete",
            "videos:read", "videos:write", "videos:delete",
            "analytics:read",
            "billing:read"
        ],
        "basic": [
            "users:read", "users:write",
            "projects:read", "projects:write",
            "videos:read", "videos:write",
            "analytics:read"
        ],
        "free": [
            "users:read",
            "projects:read", "projects:write",
            "videos:read", "videos:write"
        ]
    }

    return role_permissions.get(role, [])


class APIKeyManager:
    """API key management for external integrations."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage."""
        return get_password_hash(api_key)

    @staticmethod
    def verify_api_key(plain_key: str, hashed_key: str) -> bool:
        """Verify API key against hash."""
        return verify_password(plain_key, hashed_key)


class OAuth2Manager:
    """OAuth2 integration manager."""

    def __init__(self):
        self.providers = {
            "google": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "authorize_url": "https://accounts.google.com/o/oauth2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo"
            },
            "github": {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "authorize_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "userinfo_url": "https://api.github.com/user"
            },
            "discord": {
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "authorize_url": "https://discord.com/api/oauth2/authorize",
                "token_url": "https://discord.com/api/oauth2/token",
                "userinfo_url": "https://discord.com/api/users/@me"
            }
        }

    def get_provider_config(self, provider: str) -> Optional[Dict[str, str]]:
        """Get OAuth2 configuration for provider."""
        return self.providers.get(provider)

    def get_authorization_url(self, provider: str, redirect_uri: str) -> str:
        """Generate OAuth2 authorization URL."""
        config = self.get_provider_config(provider)
        if not config:
            raise ValueError(f"Unsupported OAuth2 provider: {provider}")

        state = secrets.token_urlsafe(32)

        return (
            f"{config['authorize_url']}?"
            f"client_id={config['client_id']}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=email profile&"
            f"response_type=code&"
            f"state={state}"
        )


class RateLimiter:
    """Rate limiting implementation using Redis."""

    def __init__(self):
        self.redis = None  # TODO: Initialize Redis connection

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            tuple: (allowed: bool, remaining: int)
        """
        # TODO: Implement Redis-based rate limiting
        # For now, return always allowed
        return True, limit - 1


# Global instances
api_key_manager = APIKeyManager()
oauth2_manager = OAuth2Manager()
rate_limiter = RateLimiter()


async def init_security() -> None:
    """Initialize security components."""
    logger.info("Security components initialized")


def require_permissions(permissions: List[str]):
    """Decorator to require specific permissions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise AuthenticationError("User not authenticated")

            if not check_permissions(current_user, permissions):
                raise AuthorizationError("Insufficient permissions")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Export commonly used functions and classes
__all__ = [
    "SecurityManager",
    "security_manager",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "check_permissions",
    "get_role_permissions",
    "APIKeyManager",
    "api_key_manager",
    "OAuth2Manager",
    "oauth2_manager",
    "RateLimiter",
    "rate_limiter",
    "init_security",
    "require_permissions",
]