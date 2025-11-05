"""
Database models and configuration
"""
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TranscriptionJob(Base):
    """Database model for transcription jobs"""
    __tablename__ = "transcription_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Job metadata
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Audio source
    audio_url = Column(Text, nullable=True)
    audio_file_path = Column(Text, nullable=True)  # S3/GCS path
    filename = Column(String(500), nullable=True)
    
    # Configuration
    engine = Column(String(50), nullable=False)
    model = Column(String(200), nullable=False)
    language = Column(String(10), nullable=False)
    diarize = Column(Boolean, default=False)
    
    # Processing options
    options = Column(JSON, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    transcription_text = Column(Text, nullable=True)
    
    # Progress and error tracking
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Webhook
    webhook_url = Column(Text, nullable=True)
    recording_id = Column(String(200), nullable=True, index=True)
    
    # User/API tracking
    api_key_id = Column(String(200), nullable=True, index=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)


class EnhancedAIJob(Base):
    """Database model for Enhanced AI processing jobs"""
    __tablename__ = "enhanced_ai_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to transcription job
    transcription_job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Job metadata
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Processing options
    options = Column(JSON, nullable=True)
    
    # LLM configuration
    llm_model = Column(String(100), nullable=True)
    temperature = Column(Integer, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    
    # Progress and error tracking
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Webhook
    webhook_url = Column(Text, nullable=True)
    
    # User/API tracking
    api_key_id = Column(String(200), nullable=True, index=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)


class APIKey(Base):
    """Database model for API keys"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Rate limiting
    rate_limit = Column(Integer, default=100)
    rate_limit_period = Column(Integer, default=3600)  # seconds
    
    # User/organization
    user_id = Column(String(200), nullable=True, index=True)
    organization_id = Column(String(200), nullable=True, index=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
