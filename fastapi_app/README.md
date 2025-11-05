# Scribe Rabbit FastAPI - Deployment Guide

## Overview

This is the transformed FastAPI version of the Scribe Rabbit transcription service, designed for deployment on AWS or GCP private cloud infrastructure.

## Architecture

The system consists of three main components:

1. **API Service** - FastAPI application handling HTTP requests
2. **Worker Service** - GPU-enabled Celery workers for transcription processing
3. **Database & Queue** - PostgreSQL for data persistence, Redis for task queue

### Two-Step Processing Pipeline

```
Step 1: Transcription (Current Implementation)
  - Audio input → ASR (Whisper models) → Diarization → Transcription output

Step 2: Enhanced_AI (Placeholder for Integration)
  - Transcription → Enhanced_AI service → Enhanced output
```

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- NVIDIA GPU (for workers)
- Docker & Docker Compose (recommended)

### Quick Start with Docker Compose

1. Clone the repository and navigate to the fastapi_app directory:
   ```bash
   cd fastapi_app
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your configuration

4. Start all services:
   ```bash
   docker-compose up
   ```

5. Access the API at http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Manual Setup (Without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start PostgreSQL and Redis:
   ```bash
   # Using Docker
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. Run database migrations:
   ```bash
   # Create database tables
   python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

4. Start the API server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. In another terminal, start a Celery worker:
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

## API Usage

### Submit Transcription Job

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/audio.mp3",
    "engine": "faster-whisper",
    "model": "ivrit-ai/whisper-large-v3-turbo-ct2",
    "language": "he",
    "diarize": true,
    "webhook_url": "https://your-app.com/webhook",
    "recording_id": "rec_12345"
  }'
```

### Check Job Status

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}" \
  -H "X-API-Key: your-api-key"
```

### Submit for Enhanced AI Processing (Placeholder)

```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-ai" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "transcription_job_id": "{job_id}",
    "enable_summarization": true,
    "enable_entity_extraction": true,
    "llm_model": "gpt-4"
  }'
```

## AWS Deployment

### Architecture

```
Client → ALB → ECS Fargate (API) → RDS PostgreSQL
                 ↓                   ↓
              Redis/ElastiCache     S3
                 ↓
          ECS (GPU Workers)
```

### Deployment Steps

1. **Create RDS PostgreSQL Instance**
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier scribe-rabbit-db \
     --db-instance-class db.t3.medium \
     --engine postgres \
     --master-username admin \
     --master-user-password yourpassword \
     --allocated-storage 20
   ```

2. **Create ElastiCache Redis Cluster**
   ```bash
   aws elasticache create-cache-cluster \
     --cache-cluster-id scribe-rabbit-redis \
     --cache-node-type cache.t3.micro \
     --engine redis \
     --num-cache-nodes 1
   ```

3. **Create S3 Bucket for Audio Files**
   ```bash
   aws s3 mb s3://scribe-rabbit-audio
   ```

4. **Build and Push Docker Images to ECR**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and push API image
   docker build -t scribe-rabbit-api -f Dockerfile .
   docker tag scribe-rabbit-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/scribe-rabbit-api:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/scribe-rabbit-api:latest
   
   # Build and push Worker image
   docker build -t scribe-rabbit-worker -f Dockerfile.worker .
   docker tag scribe-rabbit-worker:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/scribe-rabbit-worker:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/scribe-rabbit-worker:latest
   ```

5. **Create ECS Task Definitions and Services**
   - See `aws/ecs-task-definition-api.json` and `aws/ecs-task-definition-worker.json`
   - Workers should use EC2 instances with GPU (g4dn.xlarge or similar)

6. **Configure Application Load Balancer**
   - Route traffic to ECS API service
   - Set up health check to `/health`

### Terraform Configuration

See `aws/terraform/` directory for Infrastructure as Code examples.

## GCP Deployment

### Architecture

```
Client → Cloud Load Balancer → Cloud Run (API) → Cloud SQL PostgreSQL
                                    ↓                ↓
                             Memorystore Redis  Cloud Storage
                                    ↓
                          GKE with GPU Nodes (Workers)
```

### Deployment Steps

1. **Create Cloud SQL PostgreSQL Instance**
   ```bash
   gcloud sql instances create scribe-rabbit-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. **Create Memorystore Redis Instance**
   ```bash
   gcloud redis instances create scribe-rabbit-redis \
     --size=1 \
     --region=us-central1
   ```

3. **Create Cloud Storage Bucket**
   ```bash
   gsutil mb gs://scribe-rabbit-audio
   ```

4. **Build and Push Docker Images to Container Registry**
   ```bash
   # Configure Docker for GCR
   gcloud auth configure-docker
   
   # Build and push API image
   docker build -t gcr.io/<project-id>/scribe-rabbit-api -f Dockerfile .
   docker push gcr.io/<project-id>/scribe-rabbit-api
   
   # Build and push Worker image
   docker build -t gcr.io/<project-id>/scribe-rabbit-worker -f Dockerfile.worker .
   docker push gcr.io/<project-id>/scribe-rabbit-worker
   ```

5. **Deploy API to Cloud Run**
   ```bash
   gcloud run deploy scribe-rabbit-api \
     --image gcr.io/<project-id>/scribe-rabbit-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

6. **Deploy Workers to GKE with GPU**
   - Create GKE cluster with GPU node pool (T4 or A100)
   - Deploy workers using Kubernetes manifests in `gcp/kubernetes/`

### Terraform Configuration

See `gcp/terraform/` directory for Infrastructure as Code examples.

## Monitoring & Observability

### Metrics

Prometheus metrics are exposed at `/metrics`:

- `scribe_rabbit_jobs_submitted_total` - Total jobs submitted
- `scribe_rabbit_jobs_completed_total` - Total jobs completed
- `scribe_rabbit_jobs_failed_total` - Total jobs failed
- `scribe_rabbit_job_duration_seconds` - Job processing duration
- `scribe_rabbit_queue_depth` - Current queue depth

### Logging

Structured JSON logs are written to stdout and can be collected by:
- AWS CloudWatch Logs
- GCP Cloud Logging
- ELK Stack
- Datadog, New Relic, etc.

### Alerting

Configure alerts for:
- High error rates
- Long processing times
- Queue depth exceeding threshold
- Worker health issues

## Enhanced_AI Integration

The Enhanced_AI integration is currently a placeholder. To implement:

1. Update `app/services/enhanced_ai_service.py` with actual integration
2. Implement `process_enhanced_ai` task in `app/tasks.py`
3. Configure `ENHANCED_AI_ENDPOINT` and `ENHANCED_AI_API_KEY` in `.env`
4. Add any required dependencies to `requirements.txt`

Example integration structure:

```python
# app/services/enhanced_ai_service.py
class EnhancedAIService:
    def process(self, transcription_text: str, options: dict) -> dict:
        # Call Enhanced_AI service
        # Return processed results
        pass
```

## Security Considerations

1. **API Key Management**
   - Store API keys securely (AWS Secrets Manager, GCP Secret Manager)
   - Rotate keys regularly
   - Use different keys for different environments

2. **Network Security**
   - Use VPC/VPN for internal communication
   - Enable encryption in transit (TLS)
   - Restrict database access to application subnet only

3. **Data Security**
   - Encrypt data at rest (S3/Cloud Storage encryption)
   - Enable database encryption
   - Implement data retention policies

4. **Webhook Security**
   - Use HMAC signatures for webhook verification
   - Validate webhook URLs
   - Rate limit webhook endpoints

## Performance Optimization

1. **Model Caching**
   - Models are cached in worker memory
   - Use persistent volumes for model storage

2. **Concurrent Processing**
   - Scale workers horizontally based on queue depth
   - Use multiple GPU workers for parallel processing

3. **Database Connection Pooling**
   - Configure SQLAlchemy pool size based on load
   - Use read replicas for read-heavy queries

4. **Caching**
   - Cache frequently accessed data in Redis
   - Use CDN for static content

## Cost Optimization

1. **Auto-Scaling**
   - Scale down workers during low usage
   - Use spot/preemptible instances for workers

2. **Storage Lifecycle**
   - Implement automatic deletion of old audio files
   - Use cheaper storage tiers for archival

3. **GPU Optimization**
   - Use smaller GPU instances (T4) for most workloads
   - Reserve larger instances for batch processing

## Troubleshooting

### Common Issues

1. **Worker not processing jobs**
   - Check Celery worker logs
   - Verify Redis connection
   - Ensure GPU is available

2. **Database connection errors**
   - Check database credentials
   - Verify network connectivity
   - Check connection pool settings

3. **High memory usage**
   - Monitor model loading
   - Adjust worker concurrency
   - Implement model unloading for idle workers

## Support & Contributing

For issues or questions, please refer to the main repository.

## License

See LICENSE file in the root directory.
