"""
Enterprise-grade AI Model Database Models for Safwaan AI Studio
---------------------------------------------------------------

This module defines database models for AI model tracking and management with:

- Comprehensive model metadata and capabilities tracking
- Historical performance metrics and cost analysis
- Subscription tier integration
- Usage quotas and rate limiting
- Detailed generation history with metadata
- Webhook configuration persistence
- Enterprise audit logging
"""

import enum
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, 
    Integer, JSON, String, Table, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.tenant import Tenant
from app.db.models.user import User


# Enums for AI model capabilities
class VideoQualityTier(str, enum.Enum):
    """Quality tiers for video generation"""
    ECONOMY = "ECONOMY"    # Basic quality, fastest generation
    STANDARD = "STANDARD"  # Standard quality, balanced speed
    PREMIUM = "PREMIUM"    # Premium quality, slower generation
    ULTRA = "ULTRA"        # Ultra quality, business tier only


class VideoContentCategory(str, enum.Enum):
    """Content categories for model specialization"""
    GENERAL = "GENERAL"        # General purpose content
    CINEMATIC = "CINEMATIC"    # Cinematic scenes and landscapes
    ANIMATED = "ANIMATED"      # Animation and cartoon style
    PRODUCT = "PRODUCT"        # Product showcases and demos
    TUTORIAL = "TUTORIAL"      # Tutorial and how-to content
    STYLIZED = "STYLIZED"      # Artistic and stylized content


class ModelPriority(str, enum.Enum):
    """Priority levels for model selection"""
    LOW = "LOW"           # Low priority, used for free tier
    MEDIUM = "MEDIUM"     # Medium priority, used for standard tier
    HIGH = "HIGH"         # High priority, used for premium/business tier
    CRITICAL = "CRITICAL" # Critical priority, used for enterprise tier


class ModelStatus(str, enum.Enum):
    """Status of an AI model"""
    AVAILABLE = "AVAILABLE"         # Model is available and operational
    UNAVAILABLE = "UNAVAILABLE"     # Model is unavailable (API down, etc)
    MAINTENANCE = "MAINTENANCE"     # Model is undergoing maintenance
    DEPRECATED = "DEPRECATED"       # Model is deprecated and will be removed
    LIMITED = "LIMITED"             # Model has limited capacity
    OVERLOADED = "OVERLOADED"       # Model is temporarily overloaded


class VideoGenerationStatus(str, enum.Enum):
    """Status of a video generation request"""
    PENDING = "PENDING"         # Request is pending processing
    QUEUED = "QUEUED"           # Request is queued for processing
    PROCESSING = "PROCESSING"   # Request is being processed
    COMPLETED = "COMPLETED"     # Request completed successfully
    FAILED = "FAILED"           # Request failed to complete
    CANCELLED = "CANCELLED"     # Request was cancelled by user
    TIMEOUT = "TIMEOUT"         # Request timed out


# Association tables
ai_model_quality_tier_assoc = Table(
    'ai_model_quality_tier_assoc', 
    Base.metadata,
    Column('ai_model_id', ForeignKey('ai_model.id'), primary_key=True),
    Column('quality_tier', Enum(VideoQualityTier), primary_key=True)
)


ai_model_content_category_assoc = Table(
    'ai_model_content_category_assoc',
    Base.metadata,
    Column('ai_model_id', ForeignKey('ai_model.id'), primary_key=True),
    Column('content_category', Enum(VideoContentCategory), primary_key=True)
)


class AIModel(Base):
    """AI model metadata and configuration"""
    __tablename__ = "ai_model"
    
    # Core identification
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    api_path = Column(String(255), nullable=True)  # API endpoint path
    
    # Capabilities and requirements
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True)
    business_tier = Column(Boolean, default=False, nullable=False)
    
    # Status and availability
    status = Column(Enum(ModelStatus), default=ModelStatus.AVAILABLE, nullable=False)
    status_reason = Column(String(255), nullable=True)
    status_updated_at = Column(DateTime, default=datetime.utcnow)
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Performance characteristics
    quality_score = Column(Float, default=0.0, nullable=False)
    cost_per_second = Column(Float, default=0.0, nullable=False)
    average_generation_time = Column(Float, default=0.0, nullable=False)
    max_duration = Column(Float, default=60.0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    
    # Resolution support
    min_resolution_width = Column(Integer, default=256, nullable=False)
    min_resolution_height = Column(Integer, default=256, nullable=False)
    max_resolution_width = Column(Integer, default=1024, nullable=False)
    max_resolution_height = Column(Integer, default=1024, nullable=False)
    resolution_multiple = Column(Integer, default=8, nullable=False)  # Must be multiple of this
    
    # Circuit breaker configuration
    failure_threshold = Column(Integer, default=5, nullable=False)
    recovery_timeout = Column(Integer, default=300, nullable=False)  # Seconds
    
    # Rate limiting and quotas
    rate_limit = Column(Integer, default=10, nullable=False)  # Requests per minute
    daily_quota = Column(Integer, default=1000, nullable=False)  # Daily generation quota
    
    # API configuration
    api_config = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    metrics = relationship("AIModelMetrics", back_populates="model")
    generations = relationship("VideoGeneration", back_populates="model")
    quality_tiers = relationship("VideoQualityTier", secondary=ai_model_quality_tier_assoc)
    content_categories = relationship("VideoContentCategory", secondary=ai_model_content_category_assoc)
    
    def __repr__(self):
        return f"<AIModel {self.id} ({self.name} by {self.provider})>"
    
    @property
    def is_available(self):
        """Check if model is available for use"""
        return (
            self.is_enabled and 
            self.status == ModelStatus.AVAILABLE
        )
    
    @property
    def supported_resolutions(self):
        """Get list of supported resolutions"""
        resolutions = []
        
        # Generate common resolutions within the model's supported range
        common_heights = [360, 480, 576, 720, 1080, 2160]
        common_widths = [480, 640, 720, 1024, 1280, 1920, 3840]
        
        for width in common_widths:
            if (self.min_resolution_width <= width <= self.max_resolution_width and
                width % self.resolution_multiple == 0):
                for height in common_heights:
                    if (self.min_resolution_height <= height <= self.max_resolution_height and
                        height % self.resolution_multiple == 0):
                        resolutions.append((width, height))
        
        return resolutions


class AIModelMetrics(Base):
    """Historical metrics for AI model performance"""
    __tablename__ = "ai_model_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(50), ForeignKey("ai_model.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=True)
    period = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False)
    
    # Usage metrics
    request_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    average_generation_time = Column(Float, default=0.0, nullable=False)
    average_queue_time = Column(Float, default=0.0, nullable=False)
    p50_generation_time = Column(Float, default=0.0, nullable=False)
    p95_generation_time = Column(Float, default=0.0, nullable=False)
    p99_generation_time = Column(Float, default=0.0, nullable=False)
    
    # Cost metrics
    total_seconds_generated = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    
    # Additional metrics
    metrics_data = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    model = relationship("AIModel", back_populates="metrics")
    tenant = relationship("Tenant", back_populates="model_metrics")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('model_id', 'tenant_id', 'period', 'period_start', 
                        name='uix_model_tenant_period'),
    )
    
    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.request_count == 0:
            return 0.0
        return (self.success_count / self.request_count) * 100.0
    
    @property
    def average_cost_per_request(self):
        """Calculate average cost per request"""
        if self.request_count == 0:
            return 0.0
        return self.total_cost / self.request_count
    
    @property
    def period_end(self):
        """Calculate period end based on period type"""
        if self.period == "daily":
            return self.period_start + timedelta(days=1)
        elif self.period == "weekly":
            return self.period_start + timedelta(weeks=1)
        elif self.period == "monthly":
            # Approximate month as 30 days
            return self.period_start + timedelta(days=30)
        else:
            return self.period_start


class SubscriptionTierModel(Base):
    """Subscription tier definition"""
    __tablename__ = "subscription_tier"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rate limits and quotas
    api_rate_limit = Column(Integer, default=10, nullable=False)
    daily_generation_quota = Column(Integer, default=5, nullable=False)
    concurrent_generations = Column(Integer, default=1, nullable=False)
    
    # Video limits
    max_video_duration = Column(Float, default=15.0, nullable=False)
    max_resolution_width = Column(Integer, default=1024, nullable=False)
    max_resolution_height = Column(Integer, default=576, nullable=False)
    
    # Model access
    priority = Column(Enum(ModelPriority), default=ModelPriority.LOW, nullable=False)
    includes_business_models = Column(Boolean, default=False, nullable=False)
    
    # Additional features
    supports_webhooks = Column(Boolean, default=False, nullable=False)
    supports_custom_parameters = Column(Boolean, default=False, nullable=False)
    supports_priority_rendering = Column(Boolean, default=False, nullable=False)
    
    # Pricing
    monthly_price = Column(Float, default=0.0, nullable=False)
    credit_price = Column(Integer, default=0, nullable=False)
    free_credits_per_month = Column(Integer, default=0, nullable=False)
    overage_cost_per_credit = Column(Float, default=0.01, nullable=False)
    
    # Quality tiers allowed
    economy_tier_allowed = Column(Boolean, default=True, nullable=False)
    standard_tier_allowed = Column(Boolean, default=False, nullable=False)
    premium_tier_allowed = Column(Boolean, default=False, nullable=False)
    ultra_tier_allowed = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="subscription_tier")
    
    def __repr__(self):
        return f"<SubscriptionTier {self.id} ({self.name})>"
    
    @property
    def allowed_quality_tiers(self):
        """Get list of allowed quality tiers"""
        tiers = []
        
        if self.economy_tier_allowed:
            tiers.append(VideoQualityTier.ECONOMY)
            
        if self.standard_tier_allowed:
            tiers.append(VideoQualityTier.STANDARD)
            
        if self.premium_tier_allowed:
            tiers.append(VideoQualityTier.PREMIUM)
            
        if self.ultra_tier_allowed:
            tiers.append(VideoQualityTier.ULTRA)
            
        return tiers
    
    @property
    def max_resolution_str(self):
        """Get max resolution as string"""
        return f"{self.max_resolution_width}x{self.max_resolution_height}"


class WebhookConfiguration(Base):
    """Configuration for webhook notifications"""
    __tablename__ = "webhook_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    
    # Webhook settings
    name = Column(String(100), nullable=False)
    url = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Headers and authentication
    headers = Column(MutableDict.as_mutable(JSONB), default=dict)
    auth_type = Column(String(50), nullable=True)  # basic, bearer, custom
    auth_credentials = Column(Text, nullable=True)  # Encrypted credentials
    
    # Event types to trigger webhook
    trigger_on_completion = Column(Boolean, default=True, nullable=False)
    trigger_on_failure = Column(Boolean, default=True, nullable=False)
    trigger_on_status_change = Column(Boolean, default=False, nullable=False)
    
    # Retry policy
    retry_count = Column(Integer, default=3, nullable=False)
    retry_interval = Column(Integer, default=60, nullable=False)
    
    # Additional options
    include_video_data = Column(Boolean, default=False, nullable=False)
    include_metadata = Column(Boolean, default=True, nullable=False)
    format_type = Column(String(20), default="json", nullable=False)  # json, form, xml
    
    # Security
    shared_secret = Column(String(255), nullable=True)  # For signing webhooks
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="webhook_configs")
    tenant = relationship("Tenant", back_populates="webhook_configs")
    logs = relationship("WebhookDeliveryLog", back_populates="webhook_config")
    
    def __repr__(self):
        return f"<WebhookConfig {self.id} ({self.name} - {self.url})>"


class WebhookDeliveryLog(Base):
    """Log of webhook delivery attempts"""
    __tablename__ = "webhook_delivery_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhook_configuration.id"), nullable=False)
    generation_id = Column(UUID(as_uuid=True), ForeignKey("video_generation.id"), nullable=True)
    
    # Delivery attempt
    attempt_number = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # completion, failure, status_change
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    is_success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Request details
    request_url = Column(String(512), nullable=False)
    request_headers = Column(MutableDict.as_mutable(JSONB), default=dict)
    request_body = Column(Text, nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    response_time_ms = Column(Float, nullable=True)
    
    # Relationships
    webhook_config = relationship("WebhookConfiguration", back_populates="logs")
    generation = relationship("VideoGeneration", back_populates="webhook_logs")
    
    def __repr__(self):
        status = "Success" if self.is_success else f"Failed ({self.status_code})"
        return f"<WebhookDelivery {self.id} ({status} - Attempt {self.attempt_number})>"


class VideoGeneration(Base):
    """Video generation request and result tracking"""
    __tablename__ = "video_generation"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(50), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=True)
    model_id = Column(String(50), ForeignKey("ai_model.id"), nullable=True)
    
    # Generation request parameters
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    quality_tier = Column(Enum(VideoQualityTier), nullable=False)
    content_category = Column(Enum(VideoContentCategory), nullable=False)
    
    # Video properties
    duration = Column(Float, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    fps = Column(Integer, nullable=False)
    style = Column(String(100), nullable=True)
    
    # Generation parameters
    seed = Column(Integer, nullable=True)
    guidance_scale = Column(Float, nullable=True)
    motion_strength = Column(Float, nullable=True)
    custom_parameters = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    # File paths and URLs
    video_path = Column(String(512), nullable=True)
    thumbnail_path = Column(String(512), nullable=True)
    preview_path = Column(String(512), nullable=True)
    public_url = Column(String(512), nullable=True)
    thumbnail_url = Column(String(512), nullable=True)
    preview_url = Column(String(512), nullable=True)
    
    # Status and progress tracking
    status = Column(Enum(VideoGenerationStatus), default=VideoGenerationStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timing and metrics
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    queue_time_seconds = Column(Float, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)
    
    # Cost and billing
    cost = Column(Float, default=0.0, nullable=False)
    credits_used = Column(Integer, default=0, nullable=False)
    
    # Flags
    is_saved_to_gallery = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Cache and optimization
    cache_key = Column(String(255), nullable=True)
    from_cache = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    metadata = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    # Relationships
    user = relationship("User", back_populates="video_generations")
    tenant = relationship("Tenant", back_populates="video_generations")
    project = relationship("Project", back_populates="video_generations")
    model = relationship("AIModel", back_populates="generations")
    webhook_logs = relationship("WebhookDeliveryLog", back_populates="generation")
    
    def __repr__(self):
        return f"<VideoGeneration {self.id} ({self.status.value})>"
    
    @property
    def total_time_seconds(self):
        """Calculate total time from request to completion"""
        if not self.completed_at:
            return None
        
        return (self.completed_at - self.created_at).total_seconds()
    
    @property
    def resolution_str(self):
        """Get resolution as string"""
        return f"{self.width}x{self.height}"
    
    @property
    def is_completed(self):
        """Check if generation is completed"""
        return self.status == VideoGenerationStatus.COMPLETED
    
    @property
    def is_failed(self):
        """Check if generation has failed"""
        return self.status == VideoGenerationStatus.FAILED
    
    @property
    def is_processing(self):
        """Check if generation is being processed"""
        return (
            self.status == VideoGenerationStatus.PENDING or
            self.status == VideoGenerationStatus.QUEUED or
            self.status == VideoGenerationStatus.PROCESSING
        )


class UserDailyUsage(Base):
    """Daily usage tracking for quota enforcement"""
    __tablename__ = "user_daily_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Usage metrics
    generation_count = Column(Integer, default=0, nullable=False)
    seconds_generated = Column(Float, default=0.0, nullable=False)
    credits_used = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    
    # Quality tier breakdowns
    economy_tier_count = Column(Integer, default=0, nullable=False)
    standard_tier_count = Column(Integer, default=0, nullable=False)
    premium_tier_count = Column(Integer, default=0, nullable=False)
    ultra_tier_count = Column(Integer, default=0, nullable=False)
    
    # API usage
    api_requests_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="daily_usage")
    tenant = relationship("Tenant", back_populates="daily_usage")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'tenant_id', 'date', name='uix_user_tenant_date'),
    )
    
    def __repr__(self):
        return f"<UserDailyUsage {self.user_id} ({self.date.strftime('%Y-%m-%d')})>"
    
    def increment_generation(self, quality_tier, duration, cost):
        """Increment generation counters"""
        self.generation_count += 1
        self.seconds_generated += duration
        self.total_cost += cost
        self.credits_used += int(cost * 100)  # $1 = 100 credits
        
        # Increment tier-specific counter
        if quality_tier == VideoQualityTier.ECONOMY:
            self.economy_tier_count += 1
        elif quality_tier == VideoQualityTier.STANDARD:
            self.standard_tier_count += 1
        elif quality_tier == VideoQualityTier.PREMIUM:
            self.premium_tier_count += 1
        elif quality_tier == VideoQualityTier.ULTRA:
            self.ultra_tier_count += 1
    
    @classmethod
    def get_or_create(cls, db_session, user_id, tenant_id, date=None):
        """Get or create a daily usage record"""
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        usage = db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.tenant_id == tenant_id,
            cls.date == date
        ).first()
        
        if not usage:
            usage = cls(
                user_id=user_id,
                tenant_id=tenant_id,
                date=date
            )
            db_session.add(usage)
        
        return usage


class AIModelAuditLog(Base):
    """Audit log for AI model operations"""
    __tablename__ = "ai_model_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(50), ForeignKey("ai_model.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=True)
    
    # Audit details
    action = Column(String(50), nullable=False)  # create, update, delete, enable, disable
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = Column(String(255), nullable=True)
    
    # Changes
    previous_state = Column(MutableDict.as_mutable(JSONB), default=dict, nullable=True)
    new_state = Column(MutableDict.as_mutable(JSONB), default=dict, nullable=True)
    
    # Metadata
    metadata = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    def __repr__(self):
        return f"<AIModelAudit {self.id} ({self.action} on {self.model_id})>"


# Add relationship links to existing models

# Update User model with new relationships
User.subscription_tier_id = Column(String(50), ForeignKey("subscription_tier.id"), nullable=True)
User.subscription_tier = relationship("SubscriptionTierModel", back_populates="users")
User.video_generations = relationship("VideoGeneration", back_populates="user")
User.daily_usage = relationship("UserDailyUsage", back_populates="user")
User.webhook_configs = relationship("WebhookConfiguration", back_populates="user")

# Update Tenant model with new relationships
Tenant.model_metrics = relationship("AIModelMetrics", back_populates="tenant")
Tenant.video_generations = relationship("VideoGeneration", back_populates="tenant")
Tenant.daily_usage = relationship("UserDailyUsage", back_populates="tenant")
Tenant.webhook_configs = relationship("WebhookConfiguration", back_populates="tenant")

# Note: In a real implementation, you would properly handle these relationship
# additions in your migration scripts rather than direct model modification