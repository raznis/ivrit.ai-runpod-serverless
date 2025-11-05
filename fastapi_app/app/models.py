"""
Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TranscriptionEngine(str, Enum):
    """Supported transcription engines"""
    FASTER_WHISPER = "faster-whisper"
    STABLE_WHISPER = "stable-whisper"


class TranscriptionJobCreate(BaseModel):
    """Request model for creating a transcription job"""
    
    # Audio source (either url or file upload)
    url: Optional[HttpUrl] = Field(None, description="URL to audio file")
    file_upload: bool = Field(False, description="Whether this is a file upload job")
    filename: Optional[str] = Field(None, description="Original filename for uploads")
    
    # Model configuration
    engine: TranscriptionEngine = Field(
        default=TranscriptionEngine.FASTER_WHISPER,
        description="Transcription engine to use"
    )
    model: str = Field(
        default="ivrit-ai/whisper-large-v3-turbo-ct2",
        description="Model identifier"
    )
    language: str = Field(default="he", description="Language code (e.g., 'he' for Hebrew)")
    
    # Processing options
    diarize: bool = Field(default=False, description="Enable speaker diarization")
    word_timestamps: bool = Field(default=True, description="Include word-level timestamps")
    extra_data: bool = Field(default=True, description="Include extra metadata in output")
    
    # Webhook configuration
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook URL for status notifications")
    recording_id: Optional[str] = Field(None, description="Custom recording identifier for webhooks")
    
    # Additional options
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/audio.mp3",
                "engine": "faster-whisper",
                "model": "ivrit-ai/whisper-large-v3-turbo-ct2",
                "language": "he",
                "diarize": True,
                "webhook_url": "https://example.com/webhook",
                "recording_id": "rec_12345"
            }
        }


class TranscriptionJobResponse(BaseModel):
    """Response model for transcription job creation"""
    job_id: str
    status: JobStatus
    created_at: datetime
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status queries"""
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TranscriptionSegment(BaseModel):
    """A single transcription segment"""
    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Dict[str, Any]]] = None


class TranscriptionResult(BaseModel):
    """Complete transcription result"""
    text: str
    language: str
    duration: float
    segments: List[TranscriptionSegment]


class EnhancedAIJobCreate(BaseModel):
    """Request model for Enhanced AI processing (Step 2)"""
    
    transcription_job_id: str = Field(
        ..., 
        description="Job ID of the completed transcription"
    )
    
    # Enhanced AI options (placeholders)
    enable_summarization: bool = Field(default=False, description="Generate summary")
    enable_entity_extraction: bool = Field(default=False, description="Extract entities")
    enable_sentiment_analysis: bool = Field(default=False, description="Analyze sentiment")
    enable_keywords: bool = Field(default=False, description="Extract keywords")
    
    # LLM configuration
    llm_model: Optional[str] = Field(default="gpt-4", description="LLM model to use")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens for LLM response")
    
    # Custom processing
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for LLM")
    custom_instructions: Optional[Dict[str, Any]] = Field(None, description="Custom processing instructions")
    
    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook URL for completion notification")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transcription_job_id": "550e8400-e29b-41d4-a716-446655440000",
                "enable_summarization": True,
                "enable_entity_extraction": True,
                "llm_model": "gpt-4",
                "webhook_url": "https://example.com/webhook"
            }
        }


class EnhancedAIJobResponse(BaseModel):
    """Response model for Enhanced AI job creation"""
    job_id: str
    transcription_job_id: str
    status: JobStatus
    created_at: datetime
    message: str


class EnhancedAIResult(BaseModel):
    """Enhanced AI processing result (placeholder structure)"""
    summary: Optional[str] = None
    entities: Optional[List[Dict[str, Any]]] = None
    sentiment: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    custom_result: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    engine: str
    language: str
    description: str
