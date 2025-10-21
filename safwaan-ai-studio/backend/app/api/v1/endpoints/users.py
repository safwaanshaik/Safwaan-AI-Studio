"""
SAFWAAN AI STUDIO - User Management Endpoints
User profile management and administration.

This module provides:
- User profile CRUD operations
- User preferences management
- Account settings
- Admin user management
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.user import User, UserUpdate, UserPreferences
from app.services.user_service import UserService
from app.utils.exceptions import NotFoundError, AuthorizationError
from app.core.monitoring import record_error

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user profile information.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(current_user["id"])
        if not user:
            raise NotFoundError("User not found")
        return user

    except NotFoundError:
        raise
    except Exception as e:
        record_error("get_user_profile_error", "users")
        raise


@router.put("/me", response_model=User)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user profile.

    - **user_update**: User update data
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(current_user["id"], user_update)
        if not updated_user:
            raise NotFoundError("User not found")
        return updated_user

    except NotFoundError:
        raise
    except Exception as e:
        record_error("update_user_profile_error", "users")
        raise


@router.get("/me/preferences", response_model=UserPreferences)
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user preferences.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        preferences = await user_service.get_user_preferences(current_user["id"])
        return preferences

    except Exception as e:
        record_error("get_user_preferences_error", "users")
        raise


@router.put("/me/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user preferences.

    - **preferences**: User preferences data
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        updated_preferences = await user_service.update_user_preferences(
            current_user["id"], preferences
        )
        return updated_preferences

    except Exception as e:
        record_error("update_user_preferences_error", "users")
        raise


@router.delete("/me")
async def delete_current_user_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete current user account (soft delete).

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        await user_service.deactivate_user(current_user["id"])
        return {"message": "Account deactivated successfully"}

    except Exception as e:
        record_error("delete_user_account_error", "users")
        raise


# Admin endpoints
@router.get("/", response_model=List[User])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get list of users (admin only).

    - **skip**: Number of users to skip
    - **limit**: Maximum number of users to return
    - **search**: Search query for user name or email
    - **role**: Filter by user role
    - **is_active**: Filter by active status
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        users = await user_service.get_users(
            skip=skip,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active
        )
        return users

    except Exception as e:
        record_error("get_users_error", "users")
        raise


@router.get("/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user by ID (admin only).

    - **user_id**: User ID
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    except NotFoundError:
        raise
    except Exception as e:
        record_error("get_user_by_id_error", "users")
        raise


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update user by ID (admin only).

    - **user_id**: User ID
    - **user_update**: User update data
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(user_id, user_update)
        if not updated_user:
            raise NotFoundError("User not found")
        return updated_user

    except NotFoundError:
        raise
    except Exception as e:
        record_error("update_user_error", "users")
        raise


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete user by ID (admin only).

    - **user_id**: User ID
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        await user_service.delete_user(user_id)
        return {"message": "User deleted successfully"}

    except Exception as e:
        record_error("delete_user_error", "users")
        raise


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Activate user account (admin only).

    - **user_id**: User ID
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        await user_service.activate_user(user_id)
        return {"message": "User activated successfully"}

    except Exception as e:
        record_error("activate_user_error", "users")
        raise


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Deactivate user account (admin only).

    - **user_id**: User ID
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        await user_service.deactivate_user(user_id)
        return {"message": "User deactivated successfully"}

    except Exception as e:
        record_error("deactivate_user_error", "users")
        raise


@router.get("/stats/summary")
async def get_user_statistics(
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get user statistics summary (admin only).

    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        user_service = UserService(db)
        stats = await user_service.get_user_statistics()
        return stats

    except Exception as e:
        record_error("get_user_stats_error", "users")
        raise