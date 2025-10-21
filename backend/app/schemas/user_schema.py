from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=50, regex="^[a-zA-Z0-9_]+$")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    subscription_tier: str = "free"

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=8)
    email: Optional[EmailStr] = None  # Allow email to be updated
    username: Optional[str] = None  # Allow username to be updated

# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: int
    password_hash: str
    created_at: datetime
    updated_at: datetime
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: datetime

    class Config:
        from_attributes = True

# Properties to return via API
class User(UserInDBBase):
    pass

# Properties stored in DB
class UserInDB(UserInDBBase):
    pass

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None  # "access" or "refresh"

# API Key schema
class APIKey(BaseModel):
    api_key: str
    user_id: int
    name: str
    is_active: bool = True
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True