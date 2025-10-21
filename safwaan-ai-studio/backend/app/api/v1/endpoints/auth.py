"""
SAFWAAN AI STUDIO - Authentication Endpoints
JWT-based authentication with OAuth2 support.

This module provides:
- User login/logout
- Token refresh
- Password reset
- OAuth2 social login
- User registration
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_active_user,
)
from app.schemas.user import UserCreate, UserLogin, Token, User
from app.services.user_service import UserService
from app.utils.exceptions import AuthenticationError, ValidationError
from app.core.monitoring import record_error

router = APIRouter()


@router.post("/register", response_model=User)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user account.

    - **user_data**: User registration data
    - **background_tasks**: Background task queue
    - **db**: Database session
    """
    try:
        user_service = UserService(db)

        # Check if user already exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise ValidationError("User with this email already exists")

        # Create new user
        user = await user_service.create_user(user_data)

        # Send welcome email (async)
        background_tasks.add_task(send_welcome_email, user.email)

        return user

    except Exception as e:
        record_error("registration_error", "auth")
        raise


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Authenticate user and return access token.

    - **form_data**: OAuth2 form data with username and password
    - **db**: Database session
    """
    try:
        user_service = UserService(db)

        # Get user by email
        user = await user_service.get_user_by_email(form_data.username)
        if not user:
            raise AuthenticationError("Incorrect email or password")

        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "subscription_tier": user.subscription_tier
            }
        }

    except AuthenticationError:
        raise
    except Exception as e:
        record_error("login_error", "auth")
        raise AuthenticationError("Login failed")


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    - **db**: Database session
    """
    try:
        from app.core.security import verify_token

        # Verify refresh token
        payload = verify_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid refresh token")

        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except AuthenticationError:
        raise
    except Exception as e:
        record_error("token_refresh_error", "auth")
        raise AuthenticationError("Token refresh failed")


@router.post("/logout")
async def logout_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout user (client-side token invalidation).

    - **current_user**: Current authenticated user
    """
    # In a stateless JWT system, logout is handled client-side
    # In production, you might want to implement token blacklisting
    return {"message": "Successfully logged out"}


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Initiate password reset process.

    - **email**: User email address
    - **background_tasks**: Background task queue
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_email(email)

        if user:
            # Generate reset token and send email
            reset_token = create_access_token(
                data={"sub": str(user.id), "type": "password_reset"},
                expires_delta=timedelta(hours=1)
            )

            background_tasks.add_task(
                send_password_reset_email,
                user.email,
                reset_token
            )

        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}

    except Exception as e:
        record_error("password_reset_error", "auth")
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Reset user password using reset token.

    - **token**: Password reset token
    - **new_password**: New password
    - **db**: Database session
    """
    try:
        from app.core.security import verify_token

        # Verify reset token
        payload = verify_token(token)
        if payload is None or payload.get("type") != "password_reset":
            raise AuthenticationError("Invalid or expired reset token")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid reset token")

        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Update password
        hashed_password = get_password_hash(new_password)
        await user_service.update_user_password(user.id, hashed_password)

        return {"message": "Password reset successfully"}

    except AuthenticationError:
        raise
    except Exception as e:
        record_error("password_reset_error", "auth")
        raise AuthenticationError("Password reset failed")


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user information.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(current_user["id"])
        return user

    except Exception as e:
        record_error("get_user_error", "auth")
        raise


# Helper functions for email sending (implement actual email service)
async def send_welcome_email(email: str) -> None:
    """Send welcome email to new user."""
    # TODO: Implement actual email sending
    print(f"Sending welcome email to {email}")


async def send_password_reset_email(email: str, token: str) -> None:
    """Send password reset email."""
    # TODO: Implement actual email sending
    print(f"Sending password reset email to {email} with token {token}")