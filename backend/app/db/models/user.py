"""
SAFWAAN AI STUDIO - User Database Models
SQLAlchemy models for user management, authentication, and subscriptions.

This module defines all database models related to users, including authentication,
subscriptions, preferences, and usage tracking.

Author: Safwaan AI Studio Team
Version: 1.0.0
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.database import Base

# Additional imports for enhanced functionality (keeping existing for now, can be refactored later if not used)
import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import aiohttp
import numpy as np
from PIL import Image
import cv2
import torch
import requests
import time
import random
import os


class User(Base):
    """
    User model for authentication and basic user information.

    This is the main user model that stores authentication credentials
    and basic user profile information.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile fields
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Subscription and billing
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=5)

    # Security
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (Ensuring Project relationship is present)
    # Assuming other models like UserSession, UserPreferences, Subscription, Payment, CreditsTransaction exist or will be created
    # and their relationships are correctly defined.
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    credits_transactions: Mapped[List["CreditsTransaction"]] = relationship("CreditsTransaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username or self.email

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription."""
        return self.subscription_tier in ["pro", "enterprise"]


class UserSession(Base):
    """
    User session model for managing login sessions.

    Tracks active user sessions for security and session management.
    """

    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session data
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    device_info: Mapped[Optional[dict]] = mapped_column(JSON)  # Device/browser information
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv4/IPv6 support

    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at


class UserPreferences(Base):
    """
    User preferences model for storing user settings.

    Stores user interface preferences, notification settings, and other
    customizable options.
    """

    __tablename__ = "user_preferences"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # UI Preferences
    theme: Mapped[str] = mapped_column(String(50), default="dark")
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Notification Preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False)

    # Video Generation Preferences
    default_model: Mapped[str] = mapped_column(String(100), default="runwayml-gen-2")
    default_resolution: Mapped[str] = mapped_column(String(20), default="1080p")
    default_duration: Mapped[int] = mapped_column(Integer, default=10)  # seconds

    # Privacy Settings
    profile_visibility: Mapped[str] = mapped_column(String(20), default="private")  # public, private, friends
    show_email: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_data_collection: Mapped[bool] = mapped_column(Boolean, default=True)

    # Advanced Settings
    api_rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # requests per hour
    max_concurrent_jobs: Mapped[int] = mapped_column(Integer, default=3)

    # Custom preferences (JSON field for extensibility)
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreferences(user_id={self.user_id}, theme={self.theme})>"


class Subscription(Base):
    """
    Subscription model for managing user subscriptions.

    Tracks subscription details, billing cycles, and feature access.
    """

    __tablename__ = "subscriptions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Subscription details
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    tier: Mapped[str] = mapped_column(String(50), nullable=False)  # free, pro, enterprise
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, canceled, past_due, etc.

    # Billing cycle
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Feature limits
    video_limit: Mapped[int] = mapped_column(Integer, default=5)  # videos per month
    storage_limit_gb: Mapped[int] = mapped_column(Integer, default=1)  # GB
    api_calls_limit: Mapped[int] = mapped_column(Integer, default=1000)  # per month

    # Pricing
    price_cents: Mapped[int] = mapped_column(Integer, default=0)  # in cents
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional subscription data

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == "active" and not self.cancel_at_period_end

    @property
    def days_until_renewal(self) -> int:
        """Calculate days until subscription renewal."""
        now = datetime.utcnow()
        if now < self.current_period_end:
            return (self.current_period_end - now).days
        return 0


class Payment(Base):
    """
    Payment model for tracking payment transactions.

    Records all payment transactions, including successful payments,
    failed attempts, and refunds.
    """

    __tablename__ = "payments"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Payment details
    stripe_payment_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)

    # Amount and currency
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    amount_refunded_cents: Mapped[int] = mapped_column(Integer, default=0)

    # Payment status
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # succeeded, failed, pending, refunded
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))  # card, bank_account, etc.

    # Description and metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    # Failure information
    failure_code: Mapped[Optional[str]] = mapped_column(String(100))
    failure_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount_cents}, status={self.status})>"

    @property
    def amount_dollars(self) -> float:
        """Get amount in dollars."""
        return self.amount_cents / 100.0

    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == "succeeded"

    @property
    def is_refunded(self) -> bool:
        """Check if payment was refunded."""
        return self.amount_refunded_cents > 0


class CreditsTransaction(Base):
    """
    Credits transaction model for tracking credit usage and purchases.

    Records all credit-related transactions including purchases,
    usage, bonuses, and expirations.
    """

    __tablename__ = "credits_transactions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Transaction details
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Positive for credit, negative for debit
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # purchase, usage, bonus, refund, expiry

    # Description and reference
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(255))  # Payment ID, video ID, etc.

    # Balance tracking
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # For expiring credits

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="credits_transactions")

    def __repr__(self) -> str:
        return f"<CreditsTransaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type})>"

    @property
    def is_credit(self) -> bool:
        """Check if this is a credit transaction."""
        return self.amount > 0

    @property
    def is_debit(self) -> bool:
        """Check if this is a debit transaction."""
        return self.amount < 0

    @property
    def is_expired(self) -> bool:
        """Check if credits have expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


# Import other models to establish relationships
from .project import Project  # noqa: E402
from .video import Video # noqa: E402
from .ai_model import AIModel # noqa: E402
from .trend import Trend # noqa: E402
from .workflow import Workflow # noqa: E402
from .tenant import Tenant # noqa: E402