"""
Configuration settings for the FastAPI application
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Scribe Rabbit API"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_API_KEYS: List[str] = []  # Load from env or database
    WEBHOOK_SECRET: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/scribe_rabbit"
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # AWS Settings (if using AWS)
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_SQS_QUEUE_URL: Optional[str] = None
    
    # GCP Settings (if using GCP)
    GCP_PROJECT_ID: Optional[str] = None
    GCP_STORAGE_BUCKET: Optional[str] = None
    GCP_PUBSUB_TOPIC: Optional[str] = None
    
    # Transcription Settings
    MAX_FILE_SIZE_MB: int = 500
    SUPPORTED_AUDIO_FORMATS: List[str] = ["mp3", "wav", "m4a", "flac", "ogg", "webm"]
    DEFAULT_MODEL: str = "ivrit-ai/whisper-large-v3-turbo-ct2"
    DEFAULT_ENGINE: str = "faster-whisper"
    
    # Job Settings
    JOB_TIMEOUT_SECONDS: int = 3600  # 1 hour
    MAX_RETRY_ATTEMPTS: int = 3
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour
    
    # Enhanced AI Settings (Placeholder)
    ENHANCED_AI_ENDPOINT: Optional[str] = None
    ENHANCED_AI_API_KEY: Optional[str] = None
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
