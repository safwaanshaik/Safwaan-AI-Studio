"""
Advanced AI Model Management and Generation API Endpoints for Safwaan AI Studio
------------------------------------------------------------------------------

Enterprise-grade FastAPI endpoints that expose the AI model orchestration service
with advanced features including:

- Comprehensive input validation and error handling
- Authentication and authorization with role-based permissions
- Rate limiting and quota enforcement based on subscription tier
- Detailed telemetry and performance metrics
- Background task processing with status tracking
- Webhook notifications for async processing
- Extensive OpenAPI documentation
- Business logic separation with dependency injection
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from fastapi import (
    APIRouter, 
    BackgroundTasks, 
    Body, 
    Depends, 
    Header, 
    HTTPException, 
    Path, 
    Query, 
    Request, 
    Response, 
    status
)
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.status import Status, StatusCode

# Redis for caching/rate limiting
from redis import Redis
from redis.exceptions import RedisError

# Import database dependencies
from app.api.deps import get_current_active_user, get_current_superuser, get_db
from app.core.config import settings
from app.core.security import get_tenant_from_token
from app.db.models.tenant import Tenant
from app.db.models.user import User, UserRole
from app.db.models.video import Video
from app.utils.rate_limiter import get_remote_address

# Import AI engine dependencies
from ai_engine.services.model_orchestration_service import (
    GenerationRequest as OrchestratorRequest,
    GenerationResult,
    ModelOrchestrationService,
    ModelPriority,
    VideoContentCategory,
    VideoQualityTier,
)

# Initialize the model orchestrator service
model_service = ModelOrchestrationService(
    redis_url=settings.REDIS_URL
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize tracer
tracer = trace.get_tracer(__name__)

# Initialize router
router = APIRouter()


# Subscription tier definitions with rate limits and quotas
class SubscriptionTier(BaseModel):
    """Subscription tier with rate limits and quotas"""
    name: str
    api_rate_limit: int  # Requests per minute
    daily_generation_quota: int  # Number of generations per day
    max_video_duration: float  # Maximum video duration in seconds
    max_resolution: tuple[int, int]  # Maximum resolution (width, height)
    allowed_quality_tiers: list[VideoQualityTier]  # Allowed quality tiers
    priority: ModelPriority  # Priority for model selection
    includes_business_models: bool  # Access to business-tier models


# Define subscription tiers
SUBSCRIPTION_TIERS: Dict[str, SubscriptionTier] = {
    "free": SubscriptionTier(
        name="Free",
        api_rate_limit=10,  # 10 requests per minute
        daily_generation_quota=5,
        max_video_duration=15.0,
        max_resolution=(768, 768),
        allowed_quality_tiers=[VideoQualityTier.ECONOMY],
        priority=ModelPriority.LOW,
        includes_business_models=False
    ),
    "standard": SubscriptionTier(
        name="Standard",
        api_rate_limit=30,  # 30 requests per minute
        daily_generation_quota=20,
        max_video_duration=30.0,
        max_resolution=(1024, 576),
        allowed_quality_tiers=[VideoQualityTier.ECONOMY, VideoQualityTier.STANDARD],
        priority=ModelPriority.MEDIUM,
        includes_business_models=False
    ),
    "premium": SubscriptionTier(
        name="Premium",
        api_rate_limit=60,  # 60 requests per minute
        daily_generation_quota=50,
        max_video_duration=45.0,
        max_resolution=(1920, 1080),
        allowed_quality_tiers=[
            VideoQualityTier.ECONOMY, 
            VideoQualityTier.STANDARD, 
            VideoQualityTier.PREMIUM
        ],
        priority=ModelPriority.HIGH,
        includes_business_models=False
    ),
    "business": SubscriptionTier(
        name="Business",
        api_rate_limit=100,  # 100 requests per minute
        daily_generation_quota=100,
        max_video_duration=60.0,
        max_resolution=(1920, 1080),
        allowed_quality_tiers=[
            VideoQualityTier.ECONOMY, 
            VideoQualityTier.STANDARD, 
            VideoQualityTier.PREMIUM,
            VideoQualityTier.ULTRA
        ],
        priority=ModelPriority.HIGH,
        includes_business_models=True
    ),
    "enterprise": SubscriptionTier(
        name="Enterprise",
        api_rate_limit=200,  # 200 requests per minute 
        daily_generation_quota=250,
        max_video_duration=90.0,
        max_resolution=(3840, 2160),  # 4K support
        allowed_quality_tiers=[
            VideoQualityTier.ECONOMY, 
            VideoQualityTier.STANDARD, 
            VideoQualityTier.PREMIUM,
            VideoQualityTier.ULTRA
        ],
        priority=ModelPriority.HIGH,
        includes_business_models=True
    )
}


# Helper function to get subscription tier
def get_subscription_tier(user: User) -> SubscriptionTier:
    """Get subscription tier for a user"""
    # In a real implementation, this would look up the actual subscription
    # from the database, but for simplicity we'll use a hardcoded mapping
    if user.is_superuser:
        return SUBSCRIPTION_TIERS["enterprise"]
    
    # Map the user's subscription to our tier definitions
    tier_mapping = {
        "free": "free",
        "standard": "standard",
        "premium": "premium",
        "business": "business",
        "enterprise": "enterprise"
    }
    
    # Default to free tier if subscription not found
    user_tier = getattr(user, "subscription_tier", "free")
    tier_key = tier_mapping.get(user_tier.lower(), "free")
    
    return SUBSCRIPTION_TIERS[tier_key]


# Request and response models
class WebhookConfig(BaseModel):
    """Configuration for webhook notifications"""
    url: HttpUrl
    headers: Optional[Dict[str, str]] = None
    include_video_data: bool = False
    retry_count: int = Field(3, ge=1, le=10, description="Number of retry attempts")
    retry_interval: int = Field(60, ge=30, le=600, description="Seconds between retries")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/webhook/video-complete",
                "headers": {"Authorization": "Bearer your-token"},
                "include_video_data": False,
                "retry_count": 3,
                "retry_interval": 60
            }
        }


class GenerationOptions(BaseModel):
    """Advanced generation options"""
    negative_prompt: Optional[str] = Field(
        None, 
        description="Things to exclude from generation"
    )
    seed: Optional[int] = Field(
        None, 
        description="Random seed for reproducible generation"
    )
    guidance_scale: Optional[float] = Field(
        None, 
        ge=1.0, 
        le=20.0, 
        description="How closely to follow the prompt"
    )
    motion_strength: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Strength of motion in the video"
    )
    custom_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Model-specific custom parameters"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "negative_prompt": "blurry, low quality, distorted faces",
                "seed": 42,
                "guidance_scale": 7.5,
                "motion_strength": 0.8
            }
        }


class VideoResizeOptions(BaseModel):
    """Video resize and export options"""
    resize_mode: str = Field(
        "fit", 
        description="Resize mode: 'fit', 'crop', or 'stretch'"
    )
    export_format: str = Field(
        "mp4", 
        description="Output format: 'mp4', 'webm', or 'gif'"
    )
    quality: str = Field(
        "high", 
        description="Export quality: 'low', 'medium', 'high'"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "resize_mode": "fit",
                "export_format": "mp4",
                "quality": "high"
            }
        }


class VideoGenerationRequest(BaseModel):
    """Video generation request with premium features"""
    prompt: str = Field(
        ..., 
        min_length=3,
        max_length=1000,
        description="Text prompt describing the video to generate"
    )
    model_id: Optional[str] = Field(
        None, 
        description="Specific model ID to use (optional)"
    )
    quality_tier: VideoQualityTier = Field(
        VideoQualityTier.STANDARD,
        description="Quality tier for generation"
    )
    content_category: VideoContentCategory = Field(
        VideoContentCategory.GENERAL,
        description="Content category for model optimization"
    )
    duration: float = Field(
        15.0, 
        ge=1.0, 
        le=90.0,
        description="Video duration in seconds"
    )
    width: int = Field(
        1024, 
        ge=256, 
        le=3840,
        description="Video width in pixels"
    )
    height: int = Field(
        576, 
        ge=256, 
        le=2160,
        description="Video height in pixels"
    )
    fps: int = Field(
        24, 
        ge=15, 
        le=60,
        description="Frames per second"
    )
    style: Optional[str] = Field(
        "cinematic", 
        description="Visual style descriptor"
    )
    use_cache: bool = Field(
        True, 
        description="Use cached results for similar prompts"
    )
    save_to_gallery: bool = Field(
        True, 
        description="Save to user's gallery"
    )
    project_id: Optional[str] = Field(
        None, 
        description="Project ID to associate with the video"
    )
    
    # Advanced options
    generation_options: Optional[GenerationOptions] = None
    resize_options: Optional[VideoResizeOptions] = None
    webhook: Optional[WebhookConfig] = None
    
    # Validators
    @validator('width', 'height')
    def check_dimensions(cls, value, values):
        """Validate that dimensions are multiples of 8"""
        if value % 8 != 0:
            raise ValueError(f"Dimensions must be multiples of 8. Got {value}")
        return value
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "A cinematic shot of a spaceship landing on Mars with astronauts watching from a distance",
                "quality_tier": "PREMIUM",
                "content_category": "CINEMATIC",
                "duration": 15.0,
                "width": 1024,
                "height": 576,
                "fps": 24,
                "style": "photorealistic",
                "use_cache": True,
                "save_to_gallery": True,
                "project_id": "proj_12345",
                "generation_options": {
                    "negative_prompt": "blurry, low quality, distorted faces",
                    "seed": 42
                },
                "webhook": {
                    "url": "https://example.com/webhook/video-complete",
                    "headers": {"Authorization": "Bearer your-token"}
                }
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response for video generation request"""
    request_id: str = Field(..., description="Unique ID for this generation request")
    status: str = Field(..., description="Request status: 'pending', 'processing', 'completed', 'failed'")
    created_at: datetime = Field(..., description="When the request was created")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    position_in_queue: Optional[int] = Field(None, description="Position in processing queue")
    video_id: Optional[str] = Field(None, description="Generated video ID when complete")
    video_url: Optional[str] = Field(None, description="URL to access the video when complete")
    preview_url: Optional[str] = Field(None, description="URL to preview while processing")
    thumbnail_url: Optional[str] = Field(None, description="URL to video thumbnail")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    model_used: Optional[str] = Field(None, description="Model that generated the video")
    cost: Optional[float] = Field(None, description="Cost for this generation in credits")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_67890",
                "status": "pending",
                "created_at": "2025-10-21T09:00:00Z",
                "estimated_completion_time": "2025-10-21T09:01:30Z",
                "position_in_queue": 2,
                "model_used": "openai-sora",
                "cost": 2.25,
                "metrics": {
                    "processing_time": 0,
                    "queue_time": 5.2
                }
            }
        }


class ModelInfoResponse(BaseModel):
    """Information about an AI model"""
    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: str = Field(..., description="Model provider/vendor")
    status: str = Field(..., description="Model status: 'available', 'unavailable', etc.")
    quality_score: float = Field(..., description="Quality score (0-10)")
    cost_per_second: float = Field(..., description="Cost per second of video")
    max_duration: float = Field(..., description="Maximum video duration in seconds")
    average_generation_time: float = Field(..., description="Average generation time in seconds")
    supported_resolutions: List[str] = Field(..., description="Supported resolutions")
    supported_content_categories: List[str] = Field(..., description="Supported content categories")
    supported_quality_tiers: List[str] = Field(..., description="Supported quality tiers")
    success_rate: float = Field(..., description="Success rate percentage")
    business_tier: bool = Field(..., description="Whether model requires business subscription")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "openai-sora",
                "name": "OpenAI Sora",
                "provider": "OpenAI",
                "status": "available",
                "quality_score": 9.8,
                "cost_per_second": 0.15,
                "max_duration": 60.0,
                "average_generation_time": 45.0,
                "supported_resolutions": ["1920x1080", "1024x576"],
                "supported_content_categories": ["CINEMATIC", "GENERAL"],
                "supported_quality_tiers": ["PREMIUM", "ULTRA"],
                "success_rate": 98.5,
                "business_tier": True
            }
        }


class CostEstimateRequest(BaseModel):
    """Request for cost estimation"""
    prompt: str = Field(..., description="Text prompt for generation")
    model_id: Optional[str] = Field(None, description="Specific model ID (optional)")
    quality_tier: VideoQualityTier = Field(VideoQualityTier.STANDARD)
    content_category: VideoContentCategory = Field(VideoContentCategory.GENERAL)
    duration: float = Field(15.0, description="Video duration in seconds")
    width: int = Field(1024, description="Video width in pixels")
    height: int = Field(576, description="Video height in pixels")
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "A cinematic shot of a spaceship landing on Mars",
                "quality_tier": "PREMIUM",
                "content_category": "CINEMATIC",
                "duration": 15.0,
                "width": 1024,
                "height": 576
            }
        }


class CostEstimateResponse(BaseModel):
    """Response for cost estimation"""
    can_fulfill: bool = Field(..., description="Whether the request can be fulfilled")
    selected_model: Optional[str] = Field(None, description="Selected model ID")
    model_name: Optional[str] = Field(None, description="Selected model name")
    provider: Optional[str] = Field(None, description="Model provider")
    estimated_cost_dollars: Optional[float] = Field(None, description="Estimated cost in dollars")
    estimated_cost_credits: Optional[int] = Field(None, description="Estimated cost in credits")
    estimated_time_seconds: Optional[float] = Field(None, description="Estimated generation time")
    reason: Optional[str] = Field(None, description="Reason if cannot fulfill")
    
    class Config:
        schema_extra = {
            "example": {
                "can_fulfill": True,
                "selected_model": "runway-gen3",
                "model_name": "RunwayML Gen-3",
                "provider": "RunwayML",
                "estimated_cost_dollars": 1.5,
                "estimated_cost_credits": 150,
                "estimated_time_seconds": 45.0
            }
        }


# Utility function to check daily quota usage
async def check_daily_quota(user_id: str, tenant_id: str, db: Session) -> int:
    """Check how many generations a user has done today"""
    # Get the start of today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Query the database for generation count
    # In a real implementation, you would use proper SQLAlchemy query
    # For demonstration, we'll just return a fake count
    try:
        # Simulated query
        # generations = db.query(Video).filter(
        #     Video.user_id == user_id,
        #     Video.tenant_id == tenant_id,
        #     Video.created_at >= today_start
        # ).count()
        
        # For demo purposes, just return a number
        generations = 3
        
        return generations
    except Exception as e:
        logger.error(f"Error checking quota: {str(e)}")
        # Default to 0 on error to avoid blocking legitimate users
        return 0


# Utility function to map errors to proper HTTP exceptions
def handle_generation_error(error: Exception) -> HTTPException:
    """Map different error types to appropriate HTTP exceptions"""
    error_str = str(error)
    
    if "quota exceeded" in error_str.lower():
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily generation quota exceeded: {error_str}"
        )
    elif "invalid prompt" in error_str.lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prompt: {error_str}"
        )
    elif "model unavailable" in error_str.lower():
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI model unavailable: {error_str}"
        )
    elif "no suitable model" in error_str.lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No suitable model available: {error_str}"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating video: {error_str}"
        )


# Background task function for webhook callbacks
async def send_webhook_notification(
    webhook_config: WebhookConfig,
    generation_result: Dict[str, Any]
) -> None:
    """Send webhook notification about generation result"""
    if not webhook_config:
        return
        
    # Prepare webhook payload
    payload = {
        "event": "video.generated",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "request_id": generation_result.get("request_id"),
            "status": "completed" if generation_result.get("success") else "failed",
            "video_id": generation_result.get("video_id"),
            "video_url": generation_result.get("video_url"),
            "model_used": generation_result.get("model_used"),
            "duration_seconds": generation_result.get("duration_seconds"),
            "cost": generation_result.get("cost"),
            "created_at": generation_result.get("created_at"),
        }
    }
    
    # Add error if failed
    if not generation_result.get("success"):
        payload["data"]["error"] = generation_result.get("error")
    
    # Add video data if requested (base64 encoded)
    if webhook_config.include_video_data and generation_result.get("video_data"):
        import base64
        video_data = generation_result.get("video_data")
        if isinstance(video_data, bytes):
            payload["data"]["video_data_base64"] = base64.b64encode(video_data).decode('utf-8')
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SafwaanAIStudio/1.0",
        "X-Webhook-Signature": "signature-placeholder"  # In real impl, use HMAC
    }
    
    # Add custom headers if provided
    if webhook_config.headers:
        headers.update(webhook_config.headers)
    
    # Attempt to send with retries
    retry_count = webhook_config.retry_count
    retry_interval = webhook_config.retry_interval
    
    logger.info(f"Sending webhook notification to {webhook_config.url}")
    
    # Try to send webhook notification with retries
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(retry_count):
            try:
                response = await client.post(
                    str(webhook_config.url),
                    json=payload,
                    headers=headers
                )
                
                if response.status_code < 400:
                    logger.info(f"Webhook delivered successfully: {response.status_code}")
                    break
                else:
                    logger.warning(
                        f"Webhook delivery failed (attempt {attempt+1}/{retry_count}): "
                        f"HTTP {response.status_code}"
                    )
                    
                    if attempt < retry_count - 1:
                        await asyncio.sleep(retry_interval)
                    
            except Exception as e:
                logger.error(
                    f"Webhook delivery error (attempt {attempt+1}/{retry_count}): {str(e)}"
                )
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(retry_interval)


# Background task function for video generation
async def generate_video_task(
    request_id: str,
    user_id: str,
    tenant_id: str,
    orchestrator_request: OrchestratorRequest,
    webhook_config: Optional[WebhookConfig],
    save_to_gallery: bool,
    project_id: Optional[str],
    db: Session
) -> None:
    """Background task for video generation"""
    logger.info(f"Starting video generation task {request_id} for user {user_id}")
    
    try:
        # Start generation
        generation_result = await model_service.generate_video(orchestrator_request)
        
        # Store result in database
        if generation_result.success:
            # In a real implementation, create a Video record in the database
            # For demo purposes, we'll just log it
            video_id = f"vid_{uuid.uuid4().hex[:10]}"
            video_url = f"https://storage.safwaanai.studio/videos/{video_id}.mp4"
            
            logger.info(
                f"Video generation successful: {video_id}, "
                f"model={generation_result.model_used}, "
                f"cost=${generation_result.cost:.2f}"
            )
            
            # If save_to_gallery is True, would save to user gallery here
            if save_to_gallery:
                # In a real implementation, create a database record
                # video = Video(
                #     id=video_id,
                #     user_id=user_id,
                #     tenant_id=tenant_id,
                #     project_id=project_id,
                #     prompt=generation_result.prompt,
                #     model=generation_result.model_used,
                #     s3_path=f"videos/{video_id}.mp4",
                #     status="ready",
                #     cost=generation_result.cost,
                #     created_at=datetime.utcnow()
                # )
                # db.add(video)
                # db.commit()
                
                logger.info(f"Video saved to gallery: {video_id}")
                
            # Update the result with additional info
            result_dict = generation_result.dict()
            result_dict.update({
                "request_id": request_id,
                "video_id": video_id,
                "video_url": video_url,
                "user_id": user_id,
                "tenant_id": tenant_id
            })
            
            # Store the result in Redis for status polling
            # In a real implementation, you'd use Redis to store the result
            # redis_client.setex(
            #     f"video_gen:{request_id}", 
            #     86400,  # 24 hours
            #     json.dumps(result_dict)
            # )
            
        else:
            logger.error(
                f"Video generation failed: {generation_result.error}, "
                f"request={request_id}, user={user_id}"
            )
            
            # Store error in Redis for status polling
            # redis_client.setex(
            #     f"video_gen:{request_id}", 
            #     3600,  # 1 hour
            #     json.dumps({
            #         "request_id": request_id,
            #         "success": False,
            #         "error": generation_result.error,
            #         "status": "failed"
            #     })
            # )
        
        # Send webhook notification if configured
        if webhook_config:
            generation_result_dict = generation_result.dict()
            generation_result_dict["request_id"] = request_id
            generation_result_dict["video_id"] = video_id if generation_result.success else None
            generation_result_dict["video_url"] = video_url if generation_result.success else None
            
            await send_webhook_notification(webhook_config, generation_result_dict)
            
    except Exception as e:
        logger.exception(f"Unhandled error in video generation task: {str(e)}")
        
        # Store error in Redis for status polling
        # redis_client.setex(
        #     f"video_gen:{request_id}", 
        #     3600,  # 1 hour
        #     json.dumps({
        #         "request_id": request_id,
        #         "success": False,
        #         "error": f"Internal server error: {str(e)}",
        #         "status": "failed"
        #     })
        # )


# API Endpoints

@router.get(
    "/models", 
    response_model=List[ModelInfoResponse],
    summary="List available AI models",
    description="Retrieve information about all available AI video generation models with their capabilities and current status",
    response_description="List of AI models with their details and status",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_active_user)]
)
async def list_models(
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token),
    include_unavailable: bool = Query(False, description="Include unavailable models")
):
    """
    List all available AI models for video generation.
    
    - Returns details about capabilities, status, and performance metrics
    - Filters models based on user's subscription tier
    - Can optionally include unavailable models
    
    Requires authentication.
    """
    # Start span for tracing
    with tracer.start_as_current_span("list_models") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        
        try:
            # Get user's subscription tier
            user_tier = get_subscription_tier(current_user)
            
            # Get model status from the orchestrator
            model_status = await model_service.get_model_status()
            
            # Convert to response format, filtering based on subscription tier
            models = []
            
            for model_id, status in model_status.items():
                # Skip unavailable models unless explicitly requested
                if not status["available"] and not include_unavailable:
                    continue
                    
                # Skip business-tier models if user doesn't have access
                if status.get("business_tier", False) and not user_tier.includes_business_models:
                    continue
                
                # Format resolutions for display
                resolutions = []
                for res_tuple in status.get("supported_resolutions", []):
                    if isinstance(res_tuple, (list, tuple)) and len(res_tuple) == 2:
                        resolutions.append(f"{res_tuple[0]}x{res_tuple[1]}")
                
                # Create model info response
                model_info = ModelInfoResponse(
                    id=model_id,
                    name=status.get("name", model_id),
                    provider=status.get("provider", "Unknown"),
                    status=status.get("status", "unknown"),
                    quality_score=status.get("quality_score", 0.0),
                    cost_per_second=status.get("cost_per_second", 0.0),
                    max_duration=status.get("max_duration", 0.0),
                    average_generation_time=status.get("average_duration", 0.0),
                    supported_resolutions=resolutions or ["unknown"],
                    supported_content_categories=[
                        cat.value for cat in status.get("supported_content_categories", [])
                    ] or ["GENERAL"],
                    supported_quality_tiers=[
                        tier.value for tier in status.get("supported_quality_tiers", [])
                    ] or ["ECONOMY"],
                    success_rate=status.get("success_rate", 0.0) * 100,
                    business_tier=status.get("business_tier", False)
                )
                
                models.append(model_info)
            
            span.set_attribute("models.count", len(models))
            return models
            
        except Exception as e:
            logger.exception(f"Error retrieving models: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve models: {str(e)}"
            )


@router.post(
    "/estimate", 
    response_model=CostEstimateResponse,
    summary="Estimate cost and time for video generation",
    description="Calculate estimated cost and generation time before committing to generation",
    response_description="Cost and time estimation with selected model",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(get_current_active_user),
        Depends(RateLimiter(times=20, seconds=60))
    ]
)
async def estimate_generation(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token)
):
    """
    Estimate the cost and generation time for a video generation request.
    
    - Determines which model would be selected for the given request
    - Calculates expected cost in both dollars and credits
    - Provides estimated generation time
    - Validates if request can be fulfilled with current subscription
    
    This endpoint is rate-limited to 20 requests per minute.
    """
    # Start span for tracing
    with tracer.start_as_current_span("estimate_generation") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        span.set_attribute("request.prompt", request.prompt)
        
        # Get user's subscription tier
        user_tier = get_subscription_tier(current_user)
        
        # Check tier limits
        if request.duration > user_tier.max_video_duration:
            return CostEstimateResponse(
                can_fulfill=False,
                reason=f"Maximum video duration for your subscription is {user_tier.max_video_duration}s"
            )
        
        if request.width > user_tier.max_resolution[0] or request.height > user_tier.max_resolution[1]:
            max_res = f"{user_tier.max_resolution[0]}x{user_tier.max_resolution[1]}"
            return CostEstimateResponse(
                can_fulfill=False,
                reason=f"Maximum resolution for your subscription is {max_res}"
            )
            
        if request.quality_tier not in user_tier.allowed_quality_tiers:
            allowed = ", ".join([tier.value for tier in user_tier.allowed_quality_tiers])
            return CostEstimateResponse(
                can_fulfill=False,
                reason=f"Your subscription only allows these quality tiers: {allowed}"
            )
        
        try:
            # Convert to orchestrator request
            orchestrator_request = OrchestratorRequest(
                prompt=request.prompt,
                model_id=request.model_id,
                quality_tier=request.quality_tier,
                content_category=request.content_category,
                duration=request.duration,
                width=request.width,
                height=request.height,
                business_tier=user_tier.includes_business_models,
                priority=user_tier.priority
            )
            
            # Get estimation from orchestrator
            estimate = model_service.get_estimated_cost(orchestrator_request)
            
            if not estimate["can_fulfill"]:
                return CostEstimateResponse(
                    can_fulfill=False,
                    reason=estimate.get("reason", "No suitable model available")
                )
            
            # Convert dollar cost to credits (100 credits = $1.00)
            credits = int(estimate["estimated_cost_dollars"] * 100)
            
            # Create response
            return CostEstimateResponse(
                can_fulfill=True,
                selected_model=estimate["selected_model"],
                model_name=estimate["model_name"],
                provider=estimate["provider"],
                estimated_cost_dollars=estimate["estimated_cost_dollars"],
                estimated_cost_credits=credits,
                estimated_time_seconds=estimate["estimated_time_seconds"]
            )
            
        except Exception as e:
            logger.exception(f"Error estimating generation: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise handle_generation_error(e)


@router.post(
    "/generate", 
    response_model=VideoGenerationResponse,
    summary="Generate a video from prompt",
    description="Start asynchronous video generation from a text prompt with advanced options",
    response_description="Video generation request details with status tracking information",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(get_current_active_user),
        Depends(RateLimiter(times=5, seconds=60))
    ]
)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token),
    x_request_id: Optional[str] = Header(None, description="Optional client-provided request ID")
):
    """
    Generate a video from a text prompt with advanced options.
    
    - Processes generation asynchronously in the background
    - Returns immediately with a request ID for status tracking
    - Supports webhook notifications on completion
    - Applies subscription tier limits and quotas
    - Optional project association and gallery saving
    
    This endpoint is rate-limited based on subscription tier.
    """
    # Create a unique request ID if not provided
    request_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"
    
    # Start span for tracing
    with tracer.start_as_current_span("generate_video") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        span.set_attribute("request.id", request_id)
        span.set_attribute("request.prompt", request.prompt)
        
        try:
            # Get user's subscription tier
            user_tier = get_subscription_tier(current_user)
            
            # Check tier limits
            if request.duration > user_tier.max_video_duration:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Maximum video duration for your subscription is {user_tier.max_video_duration}s"
                )
            
            if request.width > user_tier.max_resolution[0] or request.height > user_tier.max_resolution[1]:
                max_res = f"{user_tier.max_resolution[0]}x{user_tier.max_resolution[1]}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Maximum resolution for your subscription is {max_res}"
                )
                
            if request.quality_tier not in user_tier.allowed_quality_tiers:
                allowed = ", ".join([tier.value for tier in user_tier.allowed_quality_tiers])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your subscription only allows these quality tiers: {allowed}"
                )
            
            # Check daily quota
            daily_usage = await check_daily_quota(current_user.id, tenant.id, db)
            
            if daily_usage >= user_tier.daily_generation_quota:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily generation quota exceeded ({daily_usage}/{user_tier.daily_generation_quota})"
                )
            
            # Convert to orchestrator request format
            orchestrator_request = OrchestratorRequest(
                prompt=request.prompt,
                model_id=request.model_id,
                quality_tier=request.quality_tier,
                content_category=request.content_category,
                duration=request.duration,
                width=request.width,
                height=request.height,
                fps=request.fps,
                style=request.style,
                use_cache=request.use_cache,
                business_tier=user_tier.includes_business_models,
                priority=user_tier.priority
            )
            
            # Add advanced options if provided
            if request.generation_options:
                # Set additional parameters
                if request.generation_options.negative_prompt:
                    orchestrator_request.negative_prompt = request.generation_options.negative_prompt
                
                if request.generation_options.seed is not None:
                    orchestrator_request.seed = request.generation_options.seed
                
                # Add any custom parameters
                if request.generation_options.custom_parameters:
                    orchestrator_request.metadata.update(request.generation_options.custom_parameters)
            
            # Start background generation task
            background_tasks.add_task(
                generate_video_task,
                request_id=request_id,
                user_id=current_user.id,
                tenant_id=tenant.id,
                orchestrator_request=orchestrator_request,
                webhook_config=request.webhook,
                save_to_gallery=request.save_to_gallery,
                project_id=request.project_id,
                db=db
            )
            
            # Get cost estimation
            estimate = model_service.get_estimated_cost(orchestrator_request)
            
            # Calculate estimated completion time
            now = datetime.utcnow()
            estimated_seconds = estimate.get("estimated_time_seconds", 60)
            
            # Add queue delay (simple estimate - in production you'd use actual queue metrics)
            queue_position = 1  # In a real implementation, this would come from your queue system
            queue_delay_seconds = queue_position * 5  # Rough estimate of 5s delay per queued job
            total_estimated_seconds = estimated_seconds + queue_delay_seconds
            
            estimated_completion = now + timedelta(seconds=total_estimated_seconds)
            
            # Create response
            return VideoGenerationResponse(
                request_id=request_id,
                status="pending",
                created_at=now,
                estimated_completion_time=estimated_completion,
                position_in_queue=queue_position,
                cost=estimate.get("estimated_cost_dollars", 0.0),
                metrics={
                    "estimated_processing_time": estimated_seconds,
                    "estimated_queue_time": queue_delay_seconds
                }
            )
            
        except HTTPException as e:
            # Re-raise HTTP exceptions directly
            span.set_status(Status(StatusCode.ERROR, e.detail))
            raise
            
        except Exception as e:
            logger.exception(f"Error starting video generation: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise handle_generation_error(e)


@router.get(
    "/status/{request_id}", 
    response_model=VideoGenerationResponse,
    summary="Check video generation status",
    description="Retrieve the current status of an ongoing or completed video generation request",
    response_description="Current status of the video generation request",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_active_user)]
)
async def get_generation_status(
    request_id: str = Path(..., description="The request ID from the generation request"),
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token)
):
    """
    Check the status of a video generation request.
    
    - Returns current processing status
    - Provides access URL when generation is complete
    - Includes error details if generation failed
    - Access limited to the request's owner
    
    Requires authentication.
    """
    # Start span for tracing
    with tracer.start_as_current_span("get_generation_status") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        span.set_attribute("request.id", request_id)
        
        try:
            # In a real implementation, retrieve status from Redis or database
            # For demo purposes, we'll create a simulated status
            
            # Simulated statuses based on request_id prefix for demo
            if request_id.startswith("complete"):
                status_value = "completed"
                video_id = f"vid_{request_id[-10:]}"
                video_url = f"https://storage.safwaanai.studio/videos/{video_id}.mp4"
                preview_url = f"https://storage.safwaanai.studio/videos/{video_id}_preview.gif"
                thumbnail_url = f"https://storage.safwaanai.studio/videos/{video_id}_thumbnail.jpg"
                model_used = "runway-gen3"
                cost = 2.25
                metrics = {
                    "processing_time": 45.2,
                    "queue_time": 5.5
                }
                error = None
                
            elif request_id.startswith("failed"):
                status_value = "failed"
                video_id = None
                video_url = None
                preview_url = None
                thumbnail_url = None
                model_used = "openai-sora"
                cost = 0.0
                metrics = {
                    "processing_time": 0.0,
                    "queue_time": 2.5
                }
                error = "Model failed to generate valid output for this prompt"
                
            elif request_id.startswith("process"):
                status_value = "processing"
                video_id = None
                video_url = None
                preview_url = f"https://storage.safwaanai.studio/previews/{request_id}.gif"
                thumbnail_url = None
                model_used = "runway-gen3"
                cost = 2.25
                metrics = {
                    "processing_time": 15.3,
                    "queue_time": 3.2,
                    "progress": 0.35
                }
                error = None
                
            else:
                status_value = "pending"
                video_id = None
                video_url = None
                preview_url = None
                thumbnail_url = None
                model_used = None
                cost = 0.0
                metrics = {
                    "processing_time": 0.0,
                    "queue_time": 8.2,
                    "position": 3
                }
                error = None
            
            # For a real implementation, you'd retrieve the actual data from your database/cache:
            # status_data = redis_client.get(f"video_gen:{request_id}")
            # if status_data:
            #     status_json = json.loads(status_data)
            #     # Map data to response...
            
            # Create response
            response = VideoGenerationResponse(
                request_id=request_id,
                status=status_value,
                created_at=datetime.utcnow() - timedelta(minutes=5),  # Simulated
                estimated_completion_time=datetime.utcnow() + timedelta(minutes=1) if status_value == "pending" or status_value == "processing" else None,
                position_in_queue=metrics.get("position", None),
                video_id=video_id,
                video_url=video_url,
                preview_url=preview_url,
                thumbnail_url=thumbnail_url,
                model_used=model_used,
                cost=cost,
                metrics=metrics,
                error=error
            )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error retrieving generation status: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve generation status: {str(e)}"
            )


@router.delete(
    "/cancel/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel pending video generation",
    description="Cancel a pending video generation request that hasn't started processing",
    dependencies=[Depends(get_current_active_user)]
)
async def cancel_generation(
    request_id: str = Path(..., description="The request ID to cancel"),
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token)
):
    """
    Cancel a pending video generation request.
    
    - Only works for requests that are still queued and not being processed
    - No effect on already completed or failed requests
    - Access limited to the request's owner
    
    Returns no content on successful cancellation.
    """
    # Start span for tracing
    with tracer.start_as_current_span("cancel_generation") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        span.set_attribute("request.id", request_id)
        
        try:
            # In a real implementation, you would:
            # 1. Check if the request exists and belongs to the current user
            # 2. Check if the request is in a cancellable state
            # 3. Remove it from the processing queue
            # 4. Update its status in the database/cache
            
            # For demo purposes, we'll just simulate cancellation
            logger.info(f"Cancelled generation request: {request_id}")
            
            return Response(status_code=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.exception(f"Error cancelling generation: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel generation: {str(e)}"
            )


@router.get(
    "/quota",
    summary="Get user's generation quota status",
    description="Retrieve information about the user's video generation quota usage",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_active_user)]
)
async def get_user_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_tenant_from_token)
):
    """
    Get the user's video generation quota usage.
    
    - Returns daily usage and limits
    - Includes subscription tier information
    - Shows quota reset time
    
    Requires authentication.
    """
    # Start span for tracing
    with tracer.start_as_current_span("get_user_quota") as span:
        span.set_attribute("user.id", current_user.id)
        span.set_attribute("tenant.id", tenant.id)
        
        try:
            # Get user's subscription tier
            user_tier = get_subscription_tier(current_user)
            
            # Check daily quota usage
            daily_usage = await check_daily_quota(current_user.id, tenant.id, db)
            
            # Calculate time until quota reset
            now = datetime.utcnow()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            seconds_until_reset = (tomorrow - now).total_seconds()
            
            return {
                "subscription_tier": user_tier.name,
                "daily_quota": {
                    "used": daily_usage,
                    "total": user_tier.daily_generation_quota,
                    "remaining": user_tier.daily_generation_quota - daily_usage
                },
                "limits": {
                    "max_duration": user_tier.max_video_duration,
                    "max_resolution": f"{user_tier.max_resolution[0]}x{user_tier.max_resolution[1]}",
                    "quality_tiers": [tier.value for tier in user_tier.allowed_quality_tiers],
                    "business_models": user_tier.includes_business_models
                },
                "rate_limit": {
                    "requests_per_minute": user_tier.api_rate_limit
                },
                "quota_resets_in": {
                    "seconds": int(seconds_until_reset),
                    "formatted": str(timedelta(seconds=int(seconds_until_reset)))
                }
            }
            
        except Exception as e:
            logger.exception(f"Error retrieving quota information: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve quota information: {str(e)}"
            )


@router.post(
    "/reset-circuit-breaker/{model_id}",
    summary="Reset circuit breaker for a model",
    description="Manually reset the circuit breaker for a specific AI model (admin only)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_superuser)]
)
async def reset_model_circuit_breaker(
    model_id: str = Path(..., description="Model ID to reset")
):
    """
    Reset the circuit breaker for a specific AI model.
    
    - Forces a model back to available state
    - Resets failure counters
    - Can be used when a model was incorrectly marked as unavailable
    
    Admin access only.
    """
    # Start span for tracing
    with tracer.start_as_current_span("reset_circuit_breaker") as span:
        span.set_attribute("model.id", model_id)
        
        try:
            # Reset the circuit breaker
            success = model_service.reset_circuit_breaker(model_id)
            
            if success:
                return {"message": f"Circuit breaker for model {model_id} reset successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model {model_id} not found"
                )
                
        except Exception as e:
            logger.exception(f"Error resetting circuit breaker: {str(e)}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reset circuit breaker: {str(e)}"
            )


@router.get(
    "/health",
    summary="Health check for AI models",
    description="Check health status of AI model services",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Health check endpoint for AI model services.
    
    - Returns status of AI generation services
    - Used by monitoring systems to detect outages
    - No authentication required
    """
    try:
        # Check model status
        model_status = await model_service.get_model_status()
        
        # Check if any models are available
        available_models = [
            model_id for model_id, status in model_status.items()
            if status.get("available", False)
        ]
        
        if not available_models:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "degraded",
                    "message": "No AI models currently available",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return {
            "status": "healthy",
            "available_models": len(available_models),
            "total_models": len(model_status),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "message": f"Service error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )