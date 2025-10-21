from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from ...core.security import oauth2_scheme, decode_token
from ...db.database import get_db
from ...db.models.user import User
from ...schemas.user_schema import UserUpdate, User as UserSchema, TokenPayload
from backend.app.core.security import get_password_hash
router = APIRouter()

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Retrieves the current authenticated user based on the provided JWT token.
    """
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get current authenticated user.
    """
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_users_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Update current authenticated user.
    """
    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data["password"])
        del update_data["password"]

    # Prevent changing email or username if they are already taken by another user
    if "email" in update_data and update_data["email"] != current_user.email:
        result = await db.execute(select(User).where(User.email == update_data["email"]))
        existing_user_email = result.scalar_one_or_none()
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user",
            )
    
    if "username" in update_data and update_data["username"] != current_user.username:
        result = await db.execute(select(User).where(User.username == update_data["username"]))
        existing_user_username = result.scalar_one_or_none()
        if existing_user_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken by another user",
            )

    stmt = update(User).where(User.id == current_user.id).values(**update_data)
    await db.execute(stmt)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.get("/{user_id}", response_model=UserSchema)
async def read_user_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Get a user by ID (admin or self-access).
    """
    if user_id == current_user.id:
        return current_user
    
    # In a real application, you'd add admin role check here
    # For now, only self-access is allowed
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this user's information",
    )