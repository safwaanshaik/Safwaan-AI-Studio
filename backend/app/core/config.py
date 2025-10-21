from pydantic import Field, EmailStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Dict, Any

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General Settings ---
    PROJECT_NAME: str = "Safwaan AI Studio"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")

    # --- Database Settings ---
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    ASYNC_DATABASE_URL: str = Field(..., env="ASYNC_DATABASE_URL")
    ECHO_SQL: bool = False

    # --- Redis Settings ---
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # --- JWT Settings ---
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- OAuth2 Settings (e.g., Google, Facebook) ---
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    FACEBOOK_CLIENT_ID: Optional[str] = Field(None, env="FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = Field(None, env="FACEBOOK_CLIENT_SECRET")
    # Add more OAuth providers as needed

    # --- AI API Keys ---
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    STABILITY_AI_API_KEY: Optional[str] = Field(None, env="STABILITY_AI_API_KEY")
    GOOGLE_GEMINI_API_KEY: Optional[str] = Field(None, env="GOOGLE_GEMINI_API_KEY")
    # Add more AI API keys as needed

    # --- Social Media Integration Keys (for sharing, etc.) ---
    TWITTER_API_KEY: Optional[str] = Field(None, env="TWITTER_API_KEY")
    TWITTER_API_SECRET: Optional[str] = Field(None, env="TWITTER_API_SECRET")
    YOUTUBE_API_KEY: Optional[str] = Field(None, env="YOUTUBE_API_KEY")
    # Add more social media keys as needed

    # --- Payment Gateway Keys (e.g., Stripe, PayPal) ---
    STRIPE_SECRET_KEY: Optional[str] = Field(None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY: Optional[str] = Field(None, env="STRIPE_PUBLIC_KEY")
    PAYPAL_CLIENT_ID: Optional[str] = Field(None, env="PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: Optional[str] = Field(None, env="PAYPAL_CLIENT_SECRET")
    # Add more payment gateway keys as needed

    # --- Email Settings (for notifications, password resets) ---
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = Field(None, env="SMTP_PORT")
    SMTP_HOST: Optional[str] = Field(None, env="SMTP_HOST")
    SMTP_USER: Optional[EmailStr] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[EmailStr] = Field(None, env="EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: Optional[str] = "Safwaan AI Studio"

    # --- CORS Settings ---
    BACKEND_CORS_ORIGINS: List[HttpUrl] = Field(
        ["http://localhost:3000", "http://localhost:8000"], env="BACKEND_CORS_ORIGINS"
    )

    # --- Logging Settings ---
    LOG_LEVEL: str = "INFO"

    # --- Admin User Settings (for initial setup or default admin) ---
    FIRST_SUPERUSER_EMAIL: EmailStr = Field("admin@example.com", env="FIRST_SUPERUSER_EMAIL")
    FIRST_SUPERUSER_PASSWORD: str = Field("changeme", env="FIRST_SUPERUSER_PASSWORD")

    # --- Cloud Storage Settings (e.g., AWS S3, Google Cloud Storage) ---
    AWS_ACCESS_KEY_ID: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = Field(None, env="AWS_REGION")
    S3_BUCKET_NAME: Optional[str] = Field(None, env="S3_BUCKET_NAME")

    # --- Webhook Secrets ---
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(None, env="STRIPE_WEBHOOK_SECRET")
    # Add more webhook secrets as needed

    # --- Feature Flags (example) ---
    ENABLE_VIDEO_EDITING: bool = True
    ENABLE_PREMIUM_FEATURES: bool = False

    # --- Custom AI Model Endpoints (if self-hosting or using specific providers) ---
    CUSTOM_AI_MODEL_ENDPOINTS: Dict[str, HttpUrl] = Field(default_factory=dict)

    # --- Error Handling Configuration ---
    SENTRY_DSN: Optional[HttpUrl] = Field(None, env="SENTRY_DSN")

    # --- Security Headers ---
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

settings = Settings()