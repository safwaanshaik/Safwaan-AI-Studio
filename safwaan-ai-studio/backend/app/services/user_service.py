"""
SAFWAAN AI STUDIO - User Service
Business logic for user management operations.

This module provides:
- User CRUD operations
- Authentication and authorization
- User preferences management
- Profile management
- User statistics and analytics
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models.user import User, UserPreferences
from app.schemas.user import UserCreate, UserUpdate, UserPreferences as UserPreferencesSchema
from app.core.security import get_password_hash
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error


class UserService:
    """Service class for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise ValidationError("User with this email already exists")

            # Create user instance
            user = User(
                email=user_data.email,
                name=user_data.name,
                hashed_password=get_password_hash(user_data.password),
                role=user_data.role or "user",
                subscription_tier=user_data.subscription_tier or "free",
                is_active=True,
                email_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            # Create default user preferences
            preferences = UserPreferences(
                user_id=user.id,
                theme="dark",
                language="en",
                timezone="UTC",
                notifications_enabled=True,
                email_notifications=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(preferences)
            await self.db.commit()

            return user

        except Exception as e:
            await self.db.rollback()
            record_error("create_user_error", "user_service")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            record_error("get_user_by_id_error", "user_service")
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            record_error("get_user_by_email_error", "user_service")
            raise

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user information."""
        try:
            # Check if user exists
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            # Prepare update data
            update_data = user_update.dict(exclude_unset=True)
            if "password" in update_data:
                update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
            update_data["updated_at"] = datetime.utcnow()

            # Update user
            query = (
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await self.db.execute(query)
            await self.db.commit()

            # Return updated user
            return await self.get_user_by_id(user_id)

        except Exception as e:
            await self.db.rollback()
            record_error("update_user_error", "user_service")
            raise

    async def update_user_password(self, user_id: str, hashed_password: str) -> None:
        """Update user password."""
        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(
                    hashed_password=hashed_password,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("update_password_error", "user_service")
            raise

    async def delete_user(self, user_id: str) -> None:
        """Permanently delete a user."""
        try:
            query = delete(User).where(User.id == user_id)
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("delete_user_error", "user_service")
            raise

    async def deactivate_user(self, user_id: str) -> None:
        """Soft delete - deactivate user account."""
        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("deactivate_user_error", "user_service")
            raise

    async def activate_user(self, user_id: str) -> None:
        """Activate user account."""
        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(
                    is_active=True,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("activate_user_error", "user_service")
            raise

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[User]:
        """Get users with filtering and pagination."""
        try:
            query = select(User)

            # Apply filters
            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    or_(
                        User.email.ilike(search_filter),
                        User.name.ilike(search_filter)
                    )
                )

            if role:
                query = query.where(User.role == role)

            if is_active is not None:
                query = query.where(User.is_active == is_active)

            # Apply sorting
            sort_column = getattr(User, sort_by, User.created_at)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            record_error("get_users_error", "user_service")
            raise

    async def get_user_preferences(self, user_id: str) -> UserPreferencesSchema:
        """Get user preferences."""
        try:
            query = select(UserPreferences).where(UserPreferences.user_id == user_id)
            result = await self.db.execute(query)
            preferences = result.scalar_one_or_none()

            if not preferences:
                # Return default preferences
                return UserPreferencesSchema(
                    theme="dark",
                    language="en",
                    timezone="UTC",
                    notifications_enabled=True,
                    email_notifications=True
                )

            return UserPreferencesSchema.from_orm(preferences)

        except Exception as e:
            record_error("get_preferences_error", "user_service")
            raise

    async def update_user_preferences(
        self,
        user_id: str,
        preferences: UserPreferencesSchema
    ) -> UserPreferencesSchema:
        """Update user preferences."""
        try:
            # Check if preferences exist
            existing = await self.get_user_preferences(user_id)

            if existing:
                # Update existing preferences
                query = (
                    update(UserPreferences)
                    .where(UserPreferences.user_id == user_id)
                    .values(
                        **preferences.dict(),
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.execute(query)
            else:
                # Create new preferences
                prefs = UserPreferences(
                    user_id=user_id,
                    **preferences.dict(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(prefs)

            await self.db.commit()
            return preferences

        except Exception as e:
            await self.db.rollback()
            record_error("update_preferences_error", "user_service")
            raise

    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get comprehensive user statistics for admin."""
        try:
            # Total users
            total_query = select(func.count(User.id))
            total_result = await self.db.execute(total_query)
            total_users = total_result.scalar()

            # Active users
            active_query = select(func.count(User.id)).where(User.is_active == True)
            active_result = await self.db.execute(active_query)
            active_users = active_result.scalar()

            # Users by role
            role_query = select(User.role, func.count(User.id)).group_by(User.role)
            role_result = await self.db.execute(role_query)
            users_by_role = dict(role_result.all())

            # Users by subscription tier
            tier_query = select(User.subscription_tier, func.count(User.id)).group_by(User.subscription_tier)
            tier_result = await self.db.execute(tier_query)
            users_by_tier = dict(tier_result.all())

            # Recent registrations (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_query = select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
            recent_result = await self.db.execute(recent_query)
            recent_registrations = recent_result.scalar()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "users_by_role": users_by_role,
                "users_by_subscription_tier": users_by_tier,
                "recent_registrations": recent_registrations,
                "activation_rate": (active_users / total_users * 100) if total_users > 0 else 0
            }

        except Exception as e:
            record_error("get_user_stats_error", "user_service")
            raise

    async def verify_email(self, user_id: str) -> None:
        """Mark user email as verified."""
        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(
                    email_verified=True,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("verify_email_error", "user_service")
            raise

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        try:
            query = (
                update(User)
                .where(User.id == user_id)
                .values(
                    last_login_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("update_last_login_error", "user_service")
            raise