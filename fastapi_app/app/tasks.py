"""
Celery tasks for asynchronous job processing
"""
from celery import Celery
from celery.utils.log import get_task_logger
import time
from typing import Dict, Any
import uuid

from .config import settings
from .database import SessionLocal
from .database import TranscriptionJob, EnhancedAIJob
from .models import JobStatus
from .services.transcription_service import TranscriptionService
from .services.webhook_service import WebhookService

logger = get_task_logger(__name__)

# Initialize Celery
celery_app = Celery(
    'scribe_rabbit',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.JOB_TIMEOUT_SECONDS,
    task_soft_time_limit=settings.JOB_TIMEOUT_SECONDS - 60,
)


def submit_transcription_task(job_id: str, job_data: Dict[str, Any]):
    """Submit a transcription task to the queue"""
    process_transcription.apply_async(
        args=[str(job_id), job_data],
        task_id=str(job_id)
    )


@celery_app.task(bind=True, max_retries=settings.MAX_RETRY_ATTEMPTS)
def process_transcription(self, job_id: str, job_data: Dict[str, Any]):
    """
    Process a transcription job
    
    This task:
    1. Loads the appropriate model
    2. Performs transcription
    3. Optionally performs diarization
    4. Stores results in database
    5. Sends webhook notifications
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting transcription job {job_id}")
        
        # Get job from database
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = time.time()
        db.commit()
        
        # Send webhook notification
        webhook_service = WebhookService()
        webhook_service.send_webhook(
            webhook_url=job.webhook_url,
            recording_id=job.recording_id,
            status='transcribing'
        )
        
        # Perform transcription
        transcription_service = TranscriptionService()
        
        result = transcription_service.transcribe(
            audio_url=job.audio_url,
            audio_file_path=job.audio_file_path,
            engine=job.engine,
            model=job.model,
            language=job.language,
            diarize=job.diarize,
            options=job.options,
            progress_callback=lambda p: update_job_progress(job_id, p)
        )
        
        # Extract text from result
        transcription_text = transcription_service.extract_transcription_text(result)
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()
        job.result = result
        job.transcription_text = transcription_text
        job.progress = 100
        db.commit()
        
        # Send completion webhook
        webhook_service.send_webhook(
            webhook_url=job.webhook_url,
            recording_id=job.recording_id,
            status='transcribed',
            transcription_text=transcription_text
        )
        
        logger.info(f"Transcription job {job_id} completed successfully")
        
        return {"status": "completed", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Error processing transcription job {job_id}: {str(e)}")
        
        # Update job status
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == uuid.UUID(job_id)).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            db.commit()
            
            # Send failure webhook
            webhook_service = WebhookService()
            webhook_service.send_webhook(
                webhook_url=job.webhook_url,
                recording_id=job.recording_id,
                status='transcription_failed',
                error=str(e)
            )
        
        # Retry if not exceeded max retries
        if job and job.retry_count < settings.MAX_RETRY_ATTEMPTS:
            logger.info(f"Retrying transcription job {job_id} (attempt {job.retry_count + 1})")
            raise self.retry(exc=e, countdown=60 * job.retry_count)
        
        raise
        
    finally:
        db.close()


def update_job_progress(job_id: str, progress: int):
    """Update job progress in database"""
    db = SessionLocal()
    try:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.id == uuid.UUID(job_id)).first()
        if job:
            job.progress = progress
            db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=settings.MAX_RETRY_ATTEMPTS)
def process_enhanced_ai(self, job_id: str, job_data: Dict[str, Any]):
    """
    Process an Enhanced AI job
    
    PLACEHOLDER: This task will be implemented when Enhanced_AI service is ready
    
    This task will:
    1. Fetch the transcription result
    2. Send to Enhanced_AI service
    3. Process LLM responses
    4. Store enhanced results
    5. Send webhook notifications
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting Enhanced AI job {job_id}")
        
        # Get job from database
        job = db.query(EnhancedAIJob).filter(EnhancedAIJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error(f"Enhanced AI job {job_id} not found in database")
            return
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = time.time()
        db.commit()
        
        # TODO: Implement Enhanced_AI processing
        # 1. Get transcription from transcription_job_id
        # 2. Call Enhanced_AI service/LLM
        # 3. Process results
        
        # Placeholder implementation
        logger.warning(f"Enhanced AI processing is not yet implemented for job {job_id}")
        
        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()
        job.result = {
            "placeholder": True,
            "message": "Enhanced AI processing not yet implemented"
        }
        job.progress = 100
        db.commit()
        
        logger.info(f"Enhanced AI job {job_id} completed (placeholder)")
        
        return {"status": "completed", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Error processing Enhanced AI job {job_id}: {str(e)}")
        
        # Update job status
        job = db.query(EnhancedAIJob).filter(EnhancedAIJob.id == uuid.UUID(job_id)).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            db.commit()
        
        raise
        
    finally:
        db.close()
