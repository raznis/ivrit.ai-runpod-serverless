"""
FastAPI Application Entry Point
Scribe Rabbit - Hebrew Transcription Service
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional
import uuid

from .config import settings
from .models import (
    TranscriptionJobCreate, 
    TranscriptionJobResponse, 
    JobStatus,
    EnhancedAIJobCreate,
    EnhancedAIJobResponse
)
from .database import engine, Base, get_db
from .tasks import submit_transcription_task
from .services.job_service import JobService
from .middleware.auth import verify_api_key
from .middleware.rate_limit import rate_limit_middleware
from . import metrics

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the FastAPI application"""
    # Startup
    logger.info("Starting Scribe Rabbit API service")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize metrics
    metrics.init_metrics()
    
    logger.info("Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Scribe Rabbit API service")


# Initialize FastAPI app
app = FastAPI(
    title="Scribe Rabbit API",
    description="Hebrew Speech-to-Text Transcription Service with Enhanced AI Processing",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "scribe-rabbit-api",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post(
    "/api/v1/transcribe",
    response_model=TranscriptionJobResponse,
    dependencies=[Depends(verify_api_key)]
)
async def create_transcription_job(
    job_request: TranscriptionJobCreate,
    background_tasks: BackgroundTasks,
    db = Depends(get_db)
):
    """
    Submit a new transcription job
    
    Supports two modes:
    - URL: Provide a URL to an audio file
    - File upload: Upload audio file directly (handled separately)
    
    The job will be processed asynchronously and results can be retrieved
    via the /api/v1/jobs/{job_id} endpoint.
    
    Webhook notifications will be sent if webhook_url is provided.
    """
    try:
        job_service = JobService(db)
        
        # Create job in database
        job = job_service.create_transcription_job(job_request)
        
        # Submit to task queue
        submit_transcription_task(job.id, job_request.dict())
        
        # Update metrics
        metrics.jobs_submitted.inc()
        
        logger.info(f"Transcription job created: {job.id}")
        
        return TranscriptionJobResponse(
            job_id=str(job.id),
            status=job.status,
            created_at=job.created_at,
            message="Job submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating transcription job: {str(e)}")
        metrics.jobs_failed.inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/transcribe/upload",
    response_model=TranscriptionJobResponse,
    dependencies=[Depends(verify_api_key)]
)
async def create_transcription_job_upload(
    file: UploadFile = File(...),
    language: str = Form("he"),
    engine: str = Form("faster-whisper"),
    model: str = Form("ivrit-ai/whisper-large-v3-turbo-ct2"),
    diarize: bool = Form(False),
    webhook_url: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db = Depends(get_db)
):
    """
    Submit a transcription job with file upload
    
    Upload an audio file directly for transcription.
    The file will be stored temporarily and processed asynchronously.
    """
    try:
        # TODO: Upload file to S3/GCS
        # For now, store file path or implement file handling
        
        job_service = JobService(db)
        
        # Create job request from form data
        job_request = TranscriptionJobCreate(
            engine=engine,
            model=model,
            language=language,
            diarize=diarize,
            webhook_url=webhook_url,
            file_upload=True,
            filename=file.filename
        )
        
        job = job_service.create_transcription_job(job_request)
        
        # TODO: Handle file upload and pass to task
        submit_transcription_task(job.id, job_request.dict())
        
        metrics.jobs_submitted.inc()
        
        logger.info(f"Transcription job created with upload: {job.id}")
        
        return TranscriptionJobResponse(
            job_id=str(job.id),
            status=job.status,
            created_at=job.created_at,
            message="Job submitted successfully with file upload"
        )
        
    except Exception as e:
        logger.error(f"Error creating transcription job with upload: {str(e)}")
        metrics.jobs_failed.inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/jobs/{job_id}",
    dependencies=[Depends(verify_api_key)]
)
async def get_job_status(
    job_id: str,
    db = Depends(get_db)
):
    """
    Get the status and details of a transcription job
    
    Returns:
    - Job status (pending, processing, completed, failed)
    - Progress information
    - Results (if completed)
    - Error details (if failed)
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        response = {
            "job_id": str(job.id),
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "progress": job.progress,
        }
        
        if job.status == JobStatus.COMPLETED:
            response["result"] = job.result
        elif job.status == JobStatus.FAILED:
            response["error"] = job.error_message
            
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/api/v1/jobs/{job_id}",
    dependencies=[Depends(verify_api_key)]
)
async def cancel_job(
    job_id: str,
    db = Depends(get_db)
):
    """
    Cancel a pending or processing job
    """
    try:
        job_service = JobService(db)
        success = job_service.cancel_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/enhanced-ai",
    response_model=EnhancedAIJobResponse,
    dependencies=[Depends(verify_api_key)]
)
async def create_enhanced_ai_job(
    job_request: EnhancedAIJobCreate,
    background_tasks: BackgroundTasks,
    db = Depends(get_db)
):
    """
    Submit transcription for Enhanced AI processing (Step 2)
    
    PLACEHOLDER: This endpoint will integrate with the Enhanced_AI service
    for advanced post-processing of transcriptions including:
    - Summarization
    - Entity extraction
    - Sentiment analysis
    - Custom enhancements
    
    The transcription_job_id should reference a completed transcription job.
    """
    try:
        job_service = JobService(db)
        
        # Verify the transcription job exists and is completed
        transcription_job = job_service.get_job(job_request.transcription_job_id)
        
        if not transcription_job:
            raise HTTPException(
                status_code=404, 
                detail="Transcription job not found"
            )
        
        if transcription_job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail="Transcription job must be completed before Enhanced AI processing"
            )
        
        # Create Enhanced AI job
        enhanced_job = job_service.create_enhanced_ai_job(job_request)
        
        # TODO: Submit to Enhanced_AI service/queue
        # submit_enhanced_ai_task(enhanced_job.id, job_request.dict())
        
        logger.info(f"Enhanced AI job created: {enhanced_job.id} for transcription: {job_request.transcription_job_id}")
        
        return EnhancedAIJobResponse(
            job_id=str(enhanced_job.id),
            transcription_job_id=job_request.transcription_job_id,
            status=enhanced_job.status,
            created_at=enhanced_job.created_at,
            message="Enhanced AI job submitted successfully (placeholder)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Enhanced AI job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/models")
async def list_models():
    """
    List available transcription models
    """
    return {
        "models": [
            {
                "id": "ivrit-ai/whisper-large-v3-turbo-ct2",
                "name": "Whisper Large V3 Turbo (Hebrew)",
                "engine": "faster-whisper",
                "language": "he",
                "description": "Optimized Hebrew transcription model (fastest)"
            },
            {
                "id": "ivrit-ai/whisper-large-v3-ct2",
                "name": "Whisper Large V3 (Hebrew)",
                "engine": "faster-whisper",
                "language": "he",
                "description": "High-accuracy Hebrew transcription model"
            },
            {
                "id": "large-v3-turbo",
                "name": "Whisper Large V3 Turbo (Multilingual)",
                "engine": "faster-whisper",
                "language": "auto",
                "description": "Fast multilingual transcription"
            }
        ]
    }


@app.post("/api/v1/webhook/test")
async def test_webhook(webhook_url: str):
    """
    Test webhook configuration by sending a test payload
    """
    import requests
    
    try:
        test_payload = {
            "recording_id": "test-" + str(uuid.uuid4()),
            "status": "test",
            "message": "This is a test webhook",
            "timestamp": None
        }
        
        response = requests.post(
            webhook_url,
            json=test_payload,
            timeout=10
        )
        
        return {
            "success": True,
            "status_code": response.status_code,
            "message": "Webhook test completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Webhook test failed"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
