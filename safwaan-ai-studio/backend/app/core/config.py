"""
SAFWAAN AI STUDIO - Configuration Management
Enterprise-grade configuration with Pydantic settings and environment validation.

This module provides centralized configuration management for all application components:
- Environment variables validation
- Database connection settings
- AI model configurations
- Security settings
- API configurations
- Monitoring and logging settings
"""

import secrets
from typing import List, Optional, Union
from pathlib import Path

from pydantic import AnyHttpUrl, field_validator, ValidationInfo, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with comprehensive validation.

    Uses Pydantic v2 with pydantic-settings for environment variable management.
    All sensitive settings are validated and type-checked.
    """

    # Application Settings
    APP_NAME: str = "Safwaan AI Studio"
    VERSION: str = "5.0.0"
    DESCRIPTION: str = "Enterprise-grade AI video generation platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True

    # Security Settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend development
        "http://localhost:8000",  # Backend development
        "https://safwaan.ai",     # Production frontend
        "https://api.safwaan.ai", # Production API
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Trusted Hosts
    ALLOWED_HOSTS: Optional[List[str]] = ["*"]

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "safwaan"
    POSTGRES_PASSWORD: str = "safwaan123"
    POSTGRES_DB: str = "safwaan_ai"
    POSTGRES_PORT: int = 5432

    # Database URL construction
    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL database URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_CACHE_DB: int = 1
    REDIS_QUEUE_DB: int = 2

    # Redis URL construction
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def REDIS_CACHE_URL(self) -> str:
        """Construct Redis cache URL."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CACHE_DB}"

    @property
    def REDIS_QUEUE_URL(self) -> str:
        """Construct Redis queue URL."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_QUEUE_DB}"

    # Celery Settings
    CELERY_BROKER_URL: str = ""  # Will be set from REDIS_QUEUE_URL
    CELERY_RESULT_BACKEND: str = ""  # Will be set from REDIS_QUEUE_URL
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000

    # AI Model Settings
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORGANIZATION: Optional[str] = None

    # RunwayML
    RUNWAYML_API_KEY: Optional[str] = None
    RUNWAYML_API_SECRET: Optional[str] = None

    # Stability AI
    STABILITY_API_KEY: Optional[str] = None

    # Tencent Hunyuan
    HUNYUAN_API_KEY: Optional[str] = None
    HUNYUAN_API_SECRET: Optional[str] = None

    # Local GPU Settings
    GPU_ENABLED: bool = False
    GPU_MEMORY_FRACTION: float = 0.8
    GPU_DEVICES: Optional[str] = None  # e.g., "0,1,2"

    # File Storage Settings
    UPLOAD_DIR: str = "/app/uploads"
    GENERATED_DIR: str = "/app/generated"
    TEMP_DIR: str = "/tmp/safwaan"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

    # Cloud Storage (AWS S3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "safwaan-ai-storage"
    S3_PUBLIC_URL: Optional[str] = None
    CLOUDFRONT_DISTRIBUTION_ID: Optional[str] = None

    # Email Settings
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    @property
    def EMAILS_ENABLED(self) -> bool:
        """Check if email is configured."""
        return bool(
            self.SMTP_HOST
            and self.SMTP_PORT
            and self.EMAILS_FROM_EMAIL
        )

    # Social Login Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    DISCORD_CLIENT_ID: Optional[str] = None
    DISCORD_CLIENT_SECRET: Optional[str] = None

    # Payment Settings (Stripe)
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_PRICE_BASIC: str = "price_basic_monthly"
    STRIPE_PRICE_PRO: str = "price_pro_monthly"
    STRIPE_PRICE_ENTERPRISE: str = "price_enterprise_monthly"

    # Subscription Settings
    FREE_CREDITS: int = 10
    BASIC_CREDITS: int = 100
    PRO_CREDITS: int = 1000
    ENTERPRISE_CREDITS: int = 10000

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_BURST: int = 20

    # API Rate Limits by Tier
    FREE_RATE_LIMIT: int = 10  # requests per minute
    BASIC_RATE_LIMIT: int = 100
    PRO_RATE_LIMIT: int = 1000
    ENTERPRISE_RATE_LIMIT: int = 10000

    # Monitoring Settings
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Analytics Settings
    ANALYTICS_ENABLED: bool = True
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "safwaan_analytics"

    # Security Settings
    ENCRYPTION_KEY: Optional[str] = None
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    SESSION_SECRET_KEY: str = secrets.token_urlsafe(32)

    # Feature Flags
    FEATURE_SOCIAL_UPLOAD: bool = True
    FEATURE_ANALYTICS: bool = True
    FEATURE_BILLING: bool = True
    FEATURE_MULTI_TENANT: bool = False
    FEATURE_PLUGIN_SYSTEM: bool = False

    # Third-party API Keys
    YOUTUBE_API_KEY: Optional[str] = None
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None

    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None

    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_CLIENT_ID: Optional[str] = None
    INSTAGRAM_CLIENT_SECRET: Optional[str] = None

    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_SECRET: Optional[str] = None

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # Webhook Settings
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_DELAY: int = 5

    # Cache Settings
    CACHE_TTL_DEFAULT: int = 300  # 5 minutes
    CACHE_TTL_USER: int = 3600    # 1 hour
    CACHE_TTL_VIDEO: int = 1800   # 30 minutes
    CACHE_TTL_ANALYTICS: int = 600  # 10 minutes

    # Background Task Settings
    TASK_TIMEOUT: int = 3600  # 1 hour
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_DELAY: int = 60  # 1 minute

    # Validation
    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings after initialization."""
        # Set Celery URLs from Redis settings
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_QUEUE_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_QUEUE_URL

        # Validate required settings for production
        if self.ENVIRONMENT == "production":
            required_settings = [
                "SECRET_KEY",
                "POSTGRES_PASSWORD",
                "REDIS_PASSWORD",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "STRIPE_API_KEY",
                "SENTRY_DSN",
            ]

            missing = []
            for setting in required_settings:
                if not getattr(self, setting, None):
                    missing.append(setting)

            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )

        # Validate AI model configurations
        ai_providers = [
            ("OPENAI_API_KEY", "OpenAI"),
            ("RUNWAYML_API_KEY", "RunwayML"),
            ("STABILITY_API_KEY", "Stability AI"),
            ("HUNYUAN_API_KEY", "Tencent Hunyuan"),
        ]

        configured_providers = [
            name for key, name in ai_providers if getattr(self, key, None)
        ]

        if not configured_providers:
            raise ValueError(
                "At least one AI provider must be configured "
                f"(supported: {', '.join(name for _, name in ai_providers)})"
            )

        return self

    # Project Paths
    @property
    def BASE_DIR(self) -> Path:
        """Get the base directory of the project."""
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def STATIC_DIR(self) -> Path:
        """Get the static files directory."""
        return self.BASE_DIR / "static"

    @property
    def MEDIA_DIR(self) -> Path:
        """Get the media files directory."""
        return self.BASE_DIR / "media"

    @property
    def LOGS_DIR(self) -> Path:
        """Get the logs directory."""
        return self.BASE_DIR / "logs"

    # Utility Methods
    def get_database_settings(self) -> dict:
        """Get database connection settings as dict."""
        return {
            "server": self.POSTGRES_SERVER,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
            "database": self.POSTGRES_DB,
            "port": self.POSTGRES_PORT,
        }

    def get_redis_settings(self) -> dict:
        """Get Redis connection settings as dict."""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "password": self.REDIS_PASSWORD,
            "db": self.REDIS_DB,
            "decode_responses": True,
        }

    def get_ai_providers(self) -> List[str]:
        """Get list of configured AI providers."""
        providers = []
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.RUNWAYML_API_KEY:
            providers.append("runwayml")
        if self.STABILITY_API_KEY:
            providers.append("stability")
        if self.HUNYUAN_API_KEY:
            providers.append("hunyuan")
        if self.GPU_ENABLED:
            providers.append("local")
        return providers

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        env_prefix = ""  # No prefix for environment variables


# Create global settings instance
settings = Settings()