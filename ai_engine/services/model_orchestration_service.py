"""
Advanced AI Model Orchestration Service for Safwaan AI Studio
-------------------------------------------------------------

This service provides enterprise-grade orchestration of multiple video generation models,
implementing intelligent model selection, fallbacks, caching, metrics, and circuit breakers.

Features:
- Intelligent model selection based on content type, quality needs, and cost constraints
- Automatic fallback mechanisms when models are unavailable or fail
- Performance and cost metrics collection
- Caching of generation results for similar prompts
- Circuit breaker pattern to prevent cascading failures
- Batching of requests for models that support it
- Resource management for GPU utilization
- Telemetry and observability integrations
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import prometheus_client as prom
from pydantic import BaseModel, Field, validator
from tenacity import (
    RetryError,
    Retrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

# Import the adapters
from ai_engine.adapters.base_adapter import BaseVideoAdapter
from ai_engine.adapters.openai_adapter import OpenAISoraAdapter
from ai_engine.adapters.runway_adapter import RunwayAdapter
from ai_engine.adapters.stability_adapter import StabilityAdapter
from ai_engine.adapters.mochi_adapter import MochiAdapter
from ai_engine.adapters.wan2_adapter import Wan2Adapter
from ai_engine.adapters.open_sora_adapter import OpenSoraAdapter

# Telemetry
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Redis for caching (optional)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logger
logger = logging.getLogger(__name__)

# Create metrics
MODEL_GENERATION_DURATION = prom.Histogram(
    'model_generation_duration_seconds',
    'Duration of video generation by model',
    ['model_name', 'success']
)

MODEL_GENERATION_COUNT = prom.Counter(
    'model_generation_count',
    'Number of video generations by model',
    ['model_name', 'success']
)

MODEL_FALLBACK_COUNT = prom.Counter(
    'model_fallback_count',
    'Number of fallbacks to backup models',
    ['primary_model', 'fallback_model']
)

MODEL_COST = prom.Counter(
    'model_cost_dollars',
    'Cost of model usage in dollars',
    ['model_name']
)

# Initialize tracer
tracer = trace.get_tracer("ai_engine.model_orchestration")


class VideoQualityTier(str, Enum):
    """Quality tiers for video generation"""
    ECONOMY = "economy"  # Basic quality, fastest generation
    STANDARD = "standard"  # Medium quality, balanced speed/quality
    PREMIUM = "premium"  # High quality, slower generation
    ULTRA = "ultra"  # Maximum quality, slowest generation


class VideoContentCategory(str, Enum):
    """Content categories for optimizing model selection"""
    GENERAL = "general"
    CINEMATIC = "cinematic"
    ANIMATION = "animation"
    PRODUCT = "product"
    LANDSCAPE = "landscape"
    PERSON = "person"
    ABSTRACT = "abstract"
    CREATIVE = "creative"
    TECHNICAL = "technical"


class VideoDurationCategory(str, Enum):
    """Duration categories for video generation"""
    SHORT = "short"  # < 15 seconds
    MEDIUM = "medium"  # 15-45 seconds
    LONG = "long"  # > 45 seconds


class ModelPriority(Enum):
    """Priority levels for model selection"""
    HIGH = 100
    MEDIUM = 50
    LOW = 10


class CircuitBreakerState(Enum):
    """Circuit breaker states for failure detection"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class ModelPerformanceStats:
    """Performance statistics for a model"""
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    total_cost: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    average_duration: float = 0.0
    
    # Circuit breaker attributes
    circuit_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_threshold: int = 3
    recovery_timeout: timedelta = timedelta(minutes=5)
    consecutive_failures: int = 0
    last_state_change_time: datetime = field(default_factory=datetime.now)
    
    def record_success(self, duration: float, cost: float) -> None:
        """Record a successful generation"""
        self.success_count += 1
        self.total_duration += duration
        self.total_cost += cost
        self.last_success_time = datetime.now()
        self.average_duration = self.total_duration / (self.success_count + 0.0001)
        
        # Reset circuit breaker on success
        if self.circuit_state == CircuitBreakerState.HALF_OPEN:
            self.circuit_state = CircuitBreakerState.CLOSED
            self.consecutive_failures = 0
            self.last_state_change_time = datetime.now()
    
    def record_failure(self) -> None:
        """Record a failed generation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        # Update circuit breaker
        if self.circuit_state == CircuitBreakerState.CLOSED:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                self.circuit_state = CircuitBreakerState.OPEN
                self.last_state_change_time = datetime.now()
                logger.warning(f"Circuit breaker opened for model due to consecutive failures")
        
    def can_use_model(self) -> bool:
        """Check if the model can be used based on circuit breaker state"""
        now = datetime.now()
        
        if self.circuit_state == CircuitBreakerState.CLOSED:
            return True
        elif self.circuit_state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if now - self.last_state_change_time >= self.recovery_timeout:
                self.circuit_state = CircuitBreakerState.HALF_OPEN
                self.last_state_change_time = now
                logger.info(f"Circuit breaker moved to half-open state for testing")
                return True
            return False
        elif self.circuit_state == CircuitBreakerState.HALF_OPEN:
            # In half-open state, allow only one test request
            return True
        
        return True  # Default case
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def status(self) -> str:
        """Get model status"""
        if not self.can_use_model():
            return "unavailable"
        
        if self.success_count + self.failure_count < 5:
            return "untested"
        
        if self.success_rate > 0.9:
            return "healthy"
        elif self.success_rate > 0.7:
            return "degraded"
        else:
            return "unhealthy"


class GenerationRequest(BaseModel):
    """Request model for video generation with advanced parameters"""
    prompt: str = Field(..., min_length=3, description="Text prompt for generation")
    model_id: Optional[str] = Field(None, description="Specific model ID to use, if preferred")
    quality_tier: VideoQualityTier = Field(VideoQualityTier.STANDARD, description="Quality tier")
    content_category: VideoContentCategory = Field(
        VideoContentCategory.GENERAL, 
        description="Content category for model optimization"
    )
    duration: float = Field(15.0, ge=1.0, le=60.0, description="Video duration in seconds")
    duration_category: Optional[VideoDurationCategory] = None
    width: int = Field(1024, description="Video width")
    height: int = Field(576, description="Video height")
    fps: int = Field(24, description="Frames per second")
    max_cost: Optional[float] = Field(None, description="Maximum cost in dollars")
    priority: ModelPriority = Field(ModelPriority.MEDIUM, description="Priority level")
    style: Optional[str] = Field(None, description="Visual style")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    seed: Optional[int] = Field(None, description="Generation seed for reproducibility")
    use_cache: bool = Field(True, description="Whether to use cache for similar prompts")
    business_tier: bool = Field(False, description="Use business-tier models only")
    
    # Additional parameters for enterprise features
    webhook_url: Optional[str] = Field(None, description="Webhook URL for async notification")
    callback_id: Optional[str] = Field(None, description="Callback ID for tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    
    # Validators
    @validator('duration_category', pre=True, always=True)
    def set_duration_category(cls, v, values):
        """Auto-set duration category based on duration if not provided"""
        if v is not None:
            return v
        
        duration = values.get('duration', 15.0)
        if duration < 15:
            return VideoDurationCategory.SHORT
        elif duration < 45:
            return VideoDurationCategory.MEDIUM
        else:
            return VideoDurationCategory.LONG
    
    def get_cache_key(self) -> str:
        """Generate a cache key for this request"""
        # Include key parameters that would affect output
        cache_dict = {
            "prompt": self.prompt,
            "quality_tier": self.quality_tier,
            "content_category": self.content_category,
            "duration_category": self.duration_category,
            "width": self.width,
            "height": self.height,
            "style": self.style,
            "negative_prompt": self.negative_prompt,
            "seed": self.seed,
        }
        
        # Create a consistent hash of the parameters
        serialized = json.dumps(cache_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


class GenerationResult(BaseModel):
    """Result model for video generation with rich metadata"""
    success: bool = Field(..., description="Whether generation was successful")
    video_url: Optional[str] = Field(None, description="URL to generated video")
    video_data: Optional[bytes] = Field(None, description="Raw video data")
    model_used: str = Field(..., description="Model that generated the video")
    prompt: str = Field(..., description="Original prompt used")
    generation_id: str = Field(..., description="Unique ID for this generation")
    created_at: datetime = Field(..., description="Generation timestamp")
    duration_seconds: float = Field(..., description="Duration of the generation in seconds")
    cost: float = Field(..., description="Cost in dollars")
    width: int = Field(..., description="Video width")
    height: int = Field(..., description="Video height")
    fps: int = Field(..., description="Frames per second")
    # Detailed metrics
    error: Optional[str] = Field(None, description="Error message if generation failed")
    model_specific_params: Dict[str, Any] = Field(default_factory=dict)
    cached: bool = Field(False, description="Whether result was retrieved from cache")
    fallbacks_used: List[str] = Field(default_factory=list, description="Fallback models tried")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Telemetry data")
    
    def get_cache_data(self) -> Dict[str, Any]:
        """Get data for caching"""
        return {
            "success": self.success,
            "video_url": self.video_url,
            "model_used": self.model_used,
            "prompt": self.prompt,
            "generation_id": self.generation_id,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "cost": self.cost,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "error": self.error,
            "model_specific_params": self.model_specific_params,
            "fallbacks_used": self.fallbacks_used,
        }


class ModelDefinition(BaseModel):
    """Definition of an AI model with capabilities and constraints"""
    id: str
    adapter: BaseVideoAdapter
    name: str
    provider: str
    quality_score: float = Field(..., ge=0.0, le=10.0)
    cost_per_second: float
    max_duration: float
    min_duration: float = 1.0
    supported_resolutions: List[Tuple[int, int]]
    supported_content_categories: Set[VideoContentCategory] = Field(default_factory=set)
    business_tier: bool = False
    supported_quality_tiers: Set[VideoQualityTier] = Field(default_factory=set)
    has_negative_prompt: bool = True
    supports_seed: bool = True
    average_generation_time: float  # In seconds
    max_concurrent_jobs: int = 5
    
    class Config:
        arbitrary_types_allowed = True

    def can_handle_request(self, request: GenerationRequest) -> bool:
        """Check if this model can handle the given request"""
        # Check business tier constraint
        if request.business_tier and not self.business_tier:
            return False
            
        # Check duration constraint
        if request.duration < self.min_duration or request.duration > self.max_duration:
            return False
            
        # Check quality tier constraint
        if request.quality_tier not in self.supported_quality_tiers:
            return False
            
        # Check content category constraint
        if len(self.supported_content_categories) > 0:
            if request.content_category not in self.supported_content_categories:
                return False
                
        # Check resolution
        request_resolution = (request.width, request.height)
        if request_resolution not in self.supported_resolutions:
            return False
            
        # Check cost constraint
        if request.max_cost is not None:
            estimated_cost = self.cost_per_second * request.duration
            if estimated_cost > request.max_cost:
                return False
                
        return True
    
    def estimated_cost(self, duration: float) -> float:
        """Estimate the cost for the given duration"""
        return self.cost_per_second * duration
    
    def estimated_generation_time(self, duration: float) -> float:
        """Estimate generation time based on video duration"""
        # Simple linear model based on video duration and average generation time
        return self.average_generation_time * (duration / 15.0)  # Normalized to 15s
        

class ModelOrchestrationService:
    """
    Enterprise-grade service for orchestrating multiple video generation models
    with intelligent routing, fallbacks, and advanced features.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.models: Dict[str, ModelDefinition] = {}
        self.performance_stats: Dict[str, ModelPerformanceStats] = {}
        self.concurrent_jobs: Dict[str, int] = {}
        self.cache_ttl = 24 * 60 * 60  # 24 hours in seconds
        
        # Initialize Redis for caching if available
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info(f"Connected to Redis cache at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
        
        # Register available adapters
        self._register_default_models()
    
    def _register_default_models(self) -> None:
        """Register the default set of video generation models"""
        # Premium tier models
        self._register_model(
            ModelDefinition(
                id="openai-sora",
                adapter=OpenAISoraAdapter(),
                name="OpenAI Sora",
                provider="OpenAI",
                quality_score=9.8,
                cost_per_second=0.15,
                max_duration=60.0,
                supported_resolutions=[(1920, 1080), (1080, 1920), (1024, 576)],
                supported_content_categories={
                    VideoContentCategory.GENERAL, VideoContentCategory.CINEMATIC,
                    VideoContentCategory.LANDSCAPE, VideoContentCategory.PERSON,
                    VideoContentCategory.CREATIVE, VideoContentCategory.PRODUCT
                },
                business_tier=True,
                supported_quality_tiers={
                    VideoQualityTier.PREMIUM, VideoQualityTier.ULTRA
                },
                average_generation_time=60.0
            )
        )
        
        self._register_model(
            ModelDefinition(
                id="runway-gen3",
                adapter=RunwayAdapter(),
                name="RunwayML Gen-3",
                provider="RunwayML",
                quality_score=9.0,
                cost_per_second=0.10,
                max_duration=45.0,
                supported_resolutions=[(1920, 1080), (1080, 1920), (768, 768)],
                supported_content_categories={
                    VideoContentCategory.GENERAL, VideoContentCategory.CINEMATIC,
                    VideoContentCategory.CREATIVE, VideoContentCategory.ANIMATION
                },
                business_tier=True,
                supported_quality_tiers={
                    VideoQualityTier.PREMIUM, VideoQualityTier.ULTRA,
                    VideoQualityTier.STANDARD
                },
                average_generation_time=45.0
            )
        )
        
        # Standard tier models
        self._register_model(
            ModelDefinition(
                id="stability-video",
                adapter=StabilityAdapter(),
                name="Stability Video",
                provider="Stability AI",
                quality_score=8.0,
                cost_per_second=0.05,
                max_duration=30.0,
                supported_resolutions=[(1024, 576), (768, 768)],
                supported_content_categories={
                    VideoContentCategory.GENERAL, VideoContentCategory.LANDSCAPE,
                    VideoContentCategory.CREATIVE
                },
                business_tier=False,
                supported_quality_tiers={
                    VideoQualityTier.STANDARD, VideoQualityTier.ECONOMY
                },
                average_generation_time=30.0
            )
        )
        
        self._register_model(
            ModelDefinition(
                id="mochi",
                adapter=MochiAdapter(),
                name="Mochi",
                provider="Genmo",
                quality_score=7.5,
                cost_per_second=0.02,
                max_duration=15.0,
                supported_resolutions=[(1024, 576), (576, 1024)],
                supported_content_categories={
                    VideoContentCategory.GENERAL, VideoContentCategory.ANIMATION
                },
                business_tier=False,
                supported_quality_tiers={
                    VideoQualityTier.STANDARD, VideoQualityTier.ECONOMY
                },
                average_generation_time=20.0
            )
        )
        
        # Economy tier models
        self._register_model(
            ModelDefinition(
                id="wan2",
                adapter=Wan2Adapter(),
                name="Wan2",
                provider="WanGenerator",
                quality_score=6.5,
                cost_per_second=0.005,
                max_duration=10.0,
                supported_resolutions=[(768, 512), (512, 768)],
                supported_content_categories={VideoContentCategory.GENERAL},
                business_tier=False,
                supported_quality_tiers={VideoQualityTier.ECONOMY},
                average_generation_time=15.0
            )
        )
        
        self._register_model(
            ModelDefinition(
                id="open-sora",
                adapter=OpenSoraAdapter(),
                name="Open-Sora",
                provider="Open Source",
                quality_score=5.0,
                cost_per_second=0.001,
                max_duration=8.0,
                supported_resolutions=[(768, 512)],
                supported_content_categories={VideoContentCategory.GENERAL},
                business_tier=False,
                supported_quality_tiers={VideoQualityTier.ECONOMY},
                average_generation_time=25.0,
                max_concurrent_jobs=10
            )
        )
        
    def _register_model(self, model: ModelDefinition) -> None:
        """Register a new model with the service"""
        self.models[model.id] = model
        self.performance_stats[model.id] = ModelPerformanceStats()
        self.concurrent_jobs[model.id] = 0
        logger.info(f"Registered model: {model.name} ({model.id})")
    
    def unregister_model(self, model_id: str) -> None:
        """Unregister a model from the service"""
        if model_id in self.models:
            del self.models[model_id]
            del self.performance_stats[model_id]
            logger.info(f"Unregistered model: {model_id}")
    
    def _get_cached_result(self, request: GenerationRequest) -> Optional[GenerationResult]:
        """Try to get a cached result for similar request"""
        if not request.use_cache or not self.redis_client:
            return None
            
        cache_key = f"video_gen:{request.get_cache_key()}"
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                data["cached"] = True
                return GenerationResult(**data)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {str(e)}")
            
        return None
    
    def _store_in_cache(self, request: GenerationRequest, result: GenerationResult) -> None:
        """Store successful result in cache"""
        if not result.success or not request.use_cache or not self.redis_client:
            return
            
        cache_key = f"video_gen:{request.get_cache_key()}"
        
        try:
            cache_data = result.get_cache_data()
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_data)
            )
            logger.debug(f"Stored result in cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage error: {str(e)}")
    
    def _calculate_model_score(self, model: ModelDefinition, request: GenerationRequest) -> float:
        """
        Calculate a score for model selection based on quality, cost, availability,
        performance history, and request priority.
        """
        if not model.can_handle_request(request):
            return -1.0
            
        # Get model stats
        stats = self.performance_stats[model.id]
        
        # Check circuit breaker
        if not stats.can_use_model():
            return -1.0
            
        # Base score from model quality
        base_score = model.quality_score * 10
        
        # Quality tier alignment score
        # Models optimized for the requested quality tier get a boost
        quality_alignment = {
            VideoQualityTier.ECONOMY: 0,
            VideoQualityTier.STANDARD: 1,
            VideoQualityTier.PREMIUM: 2,
            VideoQualityTier.ULTRA: 3
        }
        
        requested_quality = quality_alignment[request.quality_tier]
        
        if VideoQualityTier.ECONOMY in model.supported_quality_tiers:
            model_min_quality = 0
        elif VideoQualityTier.STANDARD in model.supported_quality_tiers:
            model_min_quality = 1
        elif VideoQualityTier.PREMIUM in model.supported_quality_tiers:
            model_min_quality = 2
        else:
            model_min_quality = 3
            
        if VideoQualityTier.ULTRA in model.supported_quality_tiers:
            model_max_quality = 3
        elif VideoQualityTier.PREMIUM in model.supported_quality_tiers:
            model_max_quality = 2
        elif VideoQualityTier.STANDARD in model.supported_quality_tiers:
            model_max_quality = 1
        else:
            model_max_quality = 0
            
        # Perfect quality match gets highest score
        if model_min_quality <= requested_quality <= model_max_quality:
            quality_score = 50.0
            # If it's the model's sweet spot, give extra points
            if model_min_quality == requested_quality == model_max_quality:
                quality_score += 25.0
        else:
            # Penalize models that are either too high or too low quality
            quality_score = -100.0
            
        # Cost score - lower cost is better
        cost = model.cost_per_second * request.duration
        cost_score = 100.0 / (1 + cost)
        
        # Performance score based on history
        # Higher success rate and lower generation time are better
        success_rate = stats.success_rate if stats.success_count + stats.failure_count > 0 else 0.5
        performance_score = success_rate * 30.0
        
        # Estimated generation time score
        est_time = model.estimated_generation_time(request.duration)
        time_score = 50.0 / (1 + (est_time / 60))  # Normalize to minutes
        
        # Load balancing score - prefer less busy models
        concurrent = self.concurrent_jobs[model.id]
        capacity = model.max_concurrent_jobs
        load_score = 20.0 * (1 - (concurrent / capacity))
        
        # Priority adjustment
        priority_multiplier = {
            ModelPriority.LOW: 0.8,
            ModelPriority.MEDIUM: 1.0,
            ModelPriority.HIGH: 1.2
        }[request.priority]
        
        # Content category score
        content_score = 0.0
        if len(model.supported_content_categories) > 0:
            if request.content_category in model.supported_content_categories:
                # Specialized models get a boost for their specialized categories
                specificity = 10.0 / len(model.supported_content_categories)
                content_score = 20.0 + specificity
        else:
            # General models get a moderate score
            content_score = 10.0
            
        # Calculate final score
        final_score = (
            base_score +
            quality_score +
            cost_score +
            performance_score +
            time_score +
            load_score +
            content_score
        ) * priority_multiplier
        
        logger.debug(
            f"Model {model.id} score: {final_score:.2f} (base={base_score:.2f}, "
            f"quality={quality_score:.2f}, cost={cost_score:.2f}, "
            f"perf={performance_score:.2f}, time={time_score:.2f}, "
            f"load={load_score:.2f}, content={content_score:.2f})"
        )
        
        return final_score
        
    def _select_best_model(self, request: GenerationRequest) -> Optional[ModelDefinition]:
        """Select the best model for the given request based on scoring"""
        if request.model_id and request.model_id in self.models:
            model = self.models[request.model_id]
            if model.can_handle_request(request) and self.performance_stats[model.id].can_use_model():
                logger.info(f"Using specifically requested model: {model.id}")
                return model
            else:
                logger.warning(f"Requested model {model.id} cannot handle this request or is unavailable")
                
        # Calculate scores for each available model
        model_scores = {}
        for model_id, model in self.models.items():
            score = self._calculate_model_score(model, request)
            if score > 0:
                model_scores[model_id] = score
                
        if not model_scores:
            logger.error(f"No suitable model found for request: {request.dict()}")
            return None
            
        # Sort by score (descending)
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        selected_model_id = sorted_models[0][0]
        
        logger.info(f"Selected model {selected_model_id} with score {model_scores[selected_model_id]:.2f}")
        return self.models[selected_model_id]
    
    def _get_fallback_models(self, primary_model_id: str, request: GenerationRequest) -> List[ModelDefinition]:
        """Get a list of fallback models if the primary model fails"""
        fallbacks = []
        
        # Calculate scores for potential fallbacks
        model_scores = {}
        for model_id, model in self.models.items():
            if model_id == primary_model_id:
                continue
                
            score = self._calculate_model_score(model, request)
            if score > 0:
                model_scores[model_id] = score
                
        # Sort by score (descending) and return top 2 fallbacks
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        for model_id, _ in sorted_models[:2]:
            fallbacks.append(self.models[model_id])
            
        return fallbacks
    
    async def _generate_with_model(
        self, 
        model: ModelDefinition, 
        request: GenerationRequest
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate video with the specified model"""
        model_id = model.id
        start_time = time.time()
        success = False
        result = {}
        
        # Increment concurrent job counter
        self.concurrent_jobs[model_id] += 1
        
        try:
            # Prepare parameters
            params = {
                "prompt": request.prompt,
                "duration": request.duration,
                "width": request.width,
                "height": request.height,
                "fps": request.fps,
                "style": request.style or "cinematic"
            }
            
            # Add negative prompt if supported and provided
            if model.has_negative_prompt and request.negative_prompt:
                params["negative_prompt"] = request.negative_prompt
                
            # Add seed if supported and provided
            if model.supports_seed and request.seed is not None:
                params["seed"] = request.seed
            
            # Generate video
            logger.info(f"Generating video with model {model.name} for prompt: {request.prompt}")
            response = await model.adapter.generate_video(**params)
            
            # Process result
            success = response.get("success", False)
            duration = time.time() - start_time
            
            # Calculate actual cost
            actual_cost = model.cost_per_second * request.duration
            if success:
                MODEL_COST.labels(model_id).inc(actual_cost)
                
            # Update metrics
            MODEL_GENERATION_DURATION.labels(model_id, str(success)).observe(duration)
            MODEL_GENERATION_COUNT.labels(model_id, str(success)).inc()
            
            # Update model stats
            stats = self.performance_stats[model_id]
            if success:
                stats.record_success(duration, actual_cost)
            else:
                stats.record_failure()
            
            # Build result
            result = {
                "video_url": response.get("video_url"),
                "video_data": response.get("video_data"),
                "model_used": model.name,
                "duration_seconds": duration,
                "cost": actual_cost,
                "width": request.width,
                "height": request.height,
                "fps": request.fps,
                "model_specific_params": response.get("metadata", {})
            }
            
            if not success:
                result["error"] = response.get("error", "Unknown error")
                
            logger.info(
                f"Generation with {model.name} {'succeeded' if success else 'failed'} "
                f"in {duration:.2f}s"
            )
            
            return success, result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error generating video with {model.name}: {str(e)}")
            
            # Update metrics
            MODEL_GENERATION_DURATION.labels(model_id, "False").observe(duration)
            MODEL_GENERATION_COUNT.labels(model_id, "False").inc()
            
            # Update model stats
            self.performance_stats[model_id].record_failure()
            
            return False, {"error": str(e), "duration_seconds": duration}
            
        finally:
            # Decrement concurrent job counter
            self.concurrent_jobs[model_id] -= 1
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate a video based on the request, with automatic model selection,
        fallback mechanisms, and caching.
        """
        # Create a unique generation ID
        generation_id = f"gen_{int(time.time())}_{random.randint(1000, 9999)}"
        created_at = datetime.now()
        
        # Create span for tracing
        with tracer.start_as_current_span(
            "generate_video",
            kind=SpanKind.SERVER,
            attributes={
                "request.prompt": request.prompt,
                "request.quality_tier": request.quality_tier,
                "request.content_category": request.content_category,
                "request.duration": request.duration,
                "generation_id": generation_id,
            }
        ) as span:
            # Try to get from cache first
            cached_result = self._get_cached_result(request)
            if cached_result:
                logger.info(f"Cache hit for prompt: {request.prompt[:50]}...")
                span.set_attribute("cache.hit", True)
                return cached_result
            
            span.set_attribute("cache.hit", False)
            
            # Select the best model
            primary_model = self._select_best_model(request)
            if not primary_model:
                logger.error("No suitable model found for this request")
                span.set_status(Status(StatusCode.ERROR, "No suitable model found"))
                return GenerationResult(
                    success=False,
                    model_used="none",
                    prompt=request.prompt,
                    generation_id=generation_id,
                    created_at=created_at,
                    duration_seconds=0.0,
                    cost=0.0,
                    width=request.width,
                    height=request.height,
                    fps=request.fps,
                    error="No suitable model available for this request"
                )
            
            # Get fallback models
            fallback_models = self._get_fallback_models(primary_model.id, request)
            fallbacks_used = []
            
            # Try primary model first
            span.set_attribute("model.primary", primary_model.id)
            success, result = await self._generate_with_model(primary_model, request)
            
            # If primary fails, try fallbacks
            current_model = primary_model
            if not success and fallback_models:
                for fallback_model in fallback_models:
                    fallbacks_used.append(fallback_model.id)
                    logger.info(f"Primary model failed, trying fallback: {fallback_model.id}")
                    span.set_attribute("model.fallback", fallback_model.id)
                    
                    # Record fallback metric
                    MODEL_FALLBACK_COUNT.labels(primary_model.id, fallback_model.id).inc()
                    
                    success, fallback_result = await self._generate_with_model(fallback_model, request)
                    if success:
                        logger.info(f"Fallback model {fallback_model.id} succeeded")
                        result = fallback_result
                        current_model = fallback_model
                        break
            
            # Create result object
            generation_result = GenerationResult(
                success=success,
                prompt=request.prompt,
                generation_id=generation_id,
                created_at=created_at,
                fallbacks_used=fallbacks_used,
                **result
            )
            
            # Store successful results in cache
            if success:
                self._store_in_cache(request, generation_result)
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, result.get("error", "Generation failed")))
            
            return generation_result
    
    async def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all registered models"""
        status = {}
        
        for model_id, model in self.models.items():
            stats = self.performance_stats[model_id]
            
            status[model_id] = {
                "name": model.name,
                "provider": model.provider,
                "quality_score": model.quality_score,
                "cost_per_second": model.cost_per_second,
                "status": stats.status,
                "available": model.adapter.is_available() and stats.can_use_model(),
                "success_rate": stats.success_rate,
                "success_count": stats.success_count,
                "failure_count": stats.failure_count,
                "average_duration": stats.average_duration,
                "total_cost": stats.total_cost,
                "last_success": stats.last_success_time.isoformat() if stats.last_success_time else None,
                "last_failure": stats.last_failure_time.isoformat() if stats.last_failure_time else None,
                "circuit_state": stats.circuit_state.value,
                "concurrent_jobs": self.concurrent_jobs[model_id],
            }
        
        return status
    
    def get_estimated_cost(self, request: GenerationRequest) -> Dict[str, Any]:
        """Calculate the estimated cost and generation time for a request"""
        selected_model = self._select_best_model(request)
        if not selected_model:
            return {
                "can_fulfill": False,
                "reason": "No suitable model available"
            }
            
        estimated_cost = selected_model.estimated_cost(request.duration)
        estimated_time = selected_model.estimated_generation_time(request.duration)
        
        return {
            "can_fulfill": True,
            "selected_model": selected_model.id,
            "model_name": selected_model.name,
            "provider": selected_model.provider,
            "estimated_cost_dollars": estimated_cost,
            "estimated_time_seconds": estimated_time,
            "quality_tier": request.quality_tier,
        }
        
    def reset_circuit_breaker(self, model_id: str) -> bool:
        """Manually reset circuit breaker for a model (for admin use)"""
        if model_id in self.performance_stats:
            stats = self.performance_stats[model_id]
            stats.circuit_state = CircuitBreakerState.CLOSED
            stats.consecutive_failures = 0
            stats.last_state_change_time = datetime.now()
            logger.info(f"Circuit breaker for model {model_id} manually reset")
            return True
        return False


# Example usage:
async def example_usage():
    # Initialize service
    service = ModelOrchestrationService(redis_url="redis://localhost:6379/0")
    
    # Create a request
    request = GenerationRequest(
        prompt="A cinematic shot of a spaceship landing on Mars with astronauts watching from a distance",
        quality_tier=VideoQualityTier.PREMIUM,
        content_category=VideoContentCategory.CINEMATIC,
        duration=10.0,
        width=1024,
        height=576,
        style="photorealistic",
        priority=ModelPriority.HIGH
    )
    
    # Get cost estimate
    estimate = service.get_estimated_cost(request)
    print(f"Estimated cost: ${estimate['estimated_cost_dollars']:.3f}")
    print(f"Selected model: {estimate['model_name']}")
    print(f"Estimated time: {estimate['estimated_time_seconds']:.1f} seconds")
    
    # Generate video
    result = await service.generate_video(request)
    
    # Check result
    if result.success:
        print(f"Video generated successfully! URL: {result.video_url}")
        print(f"Generated by model: {result.model_used}")
        print(f"Generation time: {result.duration_seconds:.2f} seconds")
        print(f"Cost: ${result.cost:.3f}")
    else:
        print(f"Generation failed: {result.error}")
        
    # Get model status
    status = await service.get_model_status()
    for model_id, model_status in status.items():
        print(f"{model_id}: {model_status['status']} (success rate: {model_status['success_rate']:.2f})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())