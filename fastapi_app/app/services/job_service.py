"""
Job service for managing transcription and Enhanced AI jobs
"""
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from typing import Optional

from ..database import TranscriptionJob, EnhancedAIJob
from ..models import (
    TranscriptionJobCreate, 
    JobStatus,
    EnhancedAIJobCreate
)


class JobService:
    """Service for managing jobs in the database"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_transcription_job(
        self,
        job_request: TranscriptionJobCreate,
        api_key_id: Optional[str] = None
    ) -> TranscriptionJob:
        """
        Create a new transcription job in the database
        
        Args:
            job_request: Job creation request
            api_key_id: API key used for this request
            
        Returns:
            Created TranscriptionJob instance
        """
        job = TranscriptionJob(
            id=uuid.uuid4(),
            status=JobStatus.PENDING,
            audio_url=str(job_request.url) if job_request.url else None,
            filename=job_request.filename,
            engine=job_request.engine,
            model=job_request.model,
            language=job_request.language,
            diarize=job_request.diarize,
            options={
                'word_timestamps': job_request.word_timestamps,
                'extra_data': job_request.extra_data
            },
            webhook_url=str(job_request.webhook_url) if job_request.webhook_url else None,
            recording_id=job_request.recording_id,
            api_key_id=api_key_id,
            metadata=job_request.metadata
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        """
        Get a transcription job by ID
        
        Args:
            job_id: Job UUID as string
            
        Returns:
            TranscriptionJob instance or None
        """
        try:
            return self.db.query(TranscriptionJob).filter(
                TranscriptionJob.id == uuid.UUID(job_id)
            ).first()
        except ValueError:
            return None
    
    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status
        
        Args:
            job_id: Job UUID as string
            status: New status
            error_message: Optional error message
            
        Returns:
            True if updated, False if job not found
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        job.status = status
        job.updated_at = datetime.utcnow()
        
        if error_message:
            job.error_message = error_message
        
        if status == JobStatus.PROCESSING:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job
        
        Args:
            job_id: Job UUID as string
            
        Returns:
            True if cancelled, False if job not found or cannot be cancelled
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        # Can only cancel pending or processing jobs
        if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            return False
        
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def create_enhanced_ai_job(
        self,
        job_request: EnhancedAIJobCreate,
        api_key_id: Optional[str] = None
    ) -> EnhancedAIJob:
        """
        Create a new Enhanced AI job in the database
        
        Args:
            job_request: Job creation request
            api_key_id: API key used for this request
            
        Returns:
            Created EnhancedAIJob instance
        """
        job = EnhancedAIJob(
            id=uuid.uuid4(),
            transcription_job_id=uuid.UUID(job_request.transcription_job_id),
            status=JobStatus.PENDING,
            options={
                'enable_summarization': job_request.enable_summarization,
                'enable_entity_extraction': job_request.enable_entity_extraction,
                'enable_sentiment_analysis': job_request.enable_sentiment_analysis,
                'enable_keywords': job_request.enable_keywords,
                'custom_prompt': job_request.custom_prompt,
                'custom_instructions': job_request.custom_instructions
            },
            llm_model=job_request.llm_model,
            temperature=int(job_request.temperature * 100),  # Store as int
            webhook_url=str(job_request.webhook_url) if job_request.webhook_url else None,
            api_key_id=api_key_id
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def get_enhanced_ai_job(self, job_id: str) -> Optional[EnhancedAIJob]:
        """
        Get an Enhanced AI job by ID
        
        Args:
            job_id: Job UUID as string
            
        Returns:
            EnhancedAIJob instance or None
        """
        try:
            return self.db.query(EnhancedAIJob).filter(
                EnhancedAIJob.id == uuid.UUID(job_id)
            ).first()
        except ValueError:
            return None
