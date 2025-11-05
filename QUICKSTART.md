# Quick Start Guide - FastAPI Deployment

## Getting Started in 5 Minutes

This guide will help you quickly set up and test the FastAPI-based Scribe Rabbit transcription service locally.

## Prerequisites

- Docker and Docker Compose installed
- NVIDIA Docker runtime (for GPU support - optional for API testing)
- Python 3.11+ (if running without Docker)

## Option 1: Quick Start with Docker Compose (Recommended)

### Step 1: Set Up Environment

```bash
cd fastapi_app
cp .env.example .env
```

Edit `.env` and set at minimum:
```bash
ALLOWED_API_KEYS=["test-api-key-12345"]
```

### Step 2: Start Services

```bash
# Start all services (API, workers, database, Redis)
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### Step 3: Test the API

```bash
# Health check
curl http://localhost:8000/health

# Submit a transcription job
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/metaldaniel/HebrewASR-Comparison/raw/main/HaTankistiot_n12-mp3.mp3",
    "engine": "faster-whisper",
    "model": "ivrit-ai/whisper-large-v3-turbo-ct2",
    "language": "he",
    "diarize": false
  }'

# Note the job_id from the response

# Check job status
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}" \
  -H "X-API-Key: test-api-key-12345"
```

### Step 4: View API Documentation

Open your browser to:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Step 5: Monitor

```bash
# View metrics
curl http://localhost:8000/metrics

# Check worker logs
docker-compose logs -f worker
```

### Step 6: Stop Services

```bash
docker-compose down

# To also remove data volumes
docker-compose down -v
```

---

## Option 2: Manual Setup (Without Docker)

### Step 1: Install Dependencies

```bash
cd fastapi_app
pip install -r requirements.txt
```

### Step 2: Start Infrastructure

```bash
# Start PostgreSQL
docker run -d --name scribe-postgres \
  -e POSTGRES_USER=scribe_rabbit \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scribe_rabbit \
  -p 5432:5432 \
  postgres:15

# Start Redis
docker run -d --name scribe-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
DATABASE_URL=postgresql://scribe_rabbit:password@localhost:5432/scribe_rabbit
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
ALLOWED_API_KEYS=["test-api-key-12345"]
```

### Step 4: Initialize Database

```bash
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Step 5: Start Services

Terminal 1 - API Server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Celery Worker:
```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1
```

### Step 6: Test (same as Option 1 Step 3)

---

## Testing Different Scenarios

### Test 1: Simple Transcription

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/audio.mp3",
    "language": "he",
    "diarize": false
  }'
```

### Test 2: Transcription with Diarization

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/audio.mp3",
    "language": "he",
    "diarize": true
  }'
```

### Test 3: Transcription with Webhook

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/audio.mp3",
    "language": "he",
    "webhook_url": "https://your-app.com/webhook",
    "recording_id": "rec_12345"
  }'
```

### Test 4: Enhanced AI (Placeholder)

```bash
# First, get a completed transcription job_id, then:

curl -X POST "http://localhost:8000/api/v1/enhanced-ai" \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "transcription_job_id": "{job_id}",
    "enable_summarization": true,
    "enable_entity_extraction": true
  }'
```

### Test 5: List Available Models

```bash
curl -X GET "http://localhost:8000/api/v1/models" \
  -H "X-API-Key: test-api-key-12345"
```

### Test 6: Webhook Testing

```bash
curl -X POST "http://localhost:8000/api/v1/webhook/test" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://your-app.com/webhook"}'
```

---

## Python Client Example

```python
import requests
import time

API_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Submit transcription job
response = requests.post(
    f"{API_URL}/api/v1/transcribe",
    headers=headers,
    json={
        "url": "https://example.com/audio.mp3",
        "language": "he",
        "diarize": True
    }
)

job_data = response.json()
job_id = job_data["job_id"]
print(f"Job submitted: {job_id}")

# Poll for completion
while True:
    response = requests.get(
        f"{API_URL}/api/v1/jobs/{job_id}",
        headers=headers
    )
    job_status = response.json()
    
    status = job_status["status"]
    print(f"Status: {status}")
    
    if status == "completed":
        print("Transcription:")
        print(job_status["result"])
        break
    elif status == "failed":
        print(f"Error: {job_status.get('error')}")
        break
    
    time.sleep(5)
```

---

## JavaScript/Node.js Client Example

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';
const API_KEY = 'test-api-key-12345';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

async function transcribe(audioUrl) {
  // Submit job
  const submitResponse = await axios.post(
    `${API_URL}/api/v1/transcribe`,
    {
      url: audioUrl,
      language: 'he',
      diarize: true
    },
    { headers }
  );

  const jobId = submitResponse.data.job_id;
  console.log(`Job submitted: ${jobId}`);

  // Poll for completion
  while (true) {
    const statusResponse = await axios.get(
      `${API_URL}/api/v1/jobs/${jobId}`,
      { headers }
    );

    const status = statusResponse.data.status;
    console.log(`Status: ${status}`);

    if (status === 'completed') {
      console.log('Transcription:');
      console.log(statusResponse.data.result);
      break;
    } else if (status === 'failed') {
      console.error(`Error: ${statusResponse.data.error}`);
      break;
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

transcribe('https://example.com/audio.mp3');
```

---

## Troubleshooting

### Issue: API returns 401 Unauthorized

**Solution**: Make sure you're sending the correct API key in the `X-API-Key` header and that it's listed in the `ALLOWED_API_KEYS` environment variable.

### Issue: Job stays in "pending" status

**Solution**: 
- Check if the Celery worker is running: `docker-compose logs worker`
- Verify Redis connection: `docker-compose logs redis`
- Ensure worker has GPU access (if using GPU models)

### Issue: Worker crashes with CUDA errors

**Solution**:
- Verify NVIDIA Docker runtime is installed
- Check GPU availability: `nvidia-smi`
- Try using CPU-only mode first for testing

### Issue: Database connection errors

**Solution**:
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check DATABASE_URL in `.env` is correct
- Ensure database was initialized

### Issue: "Model not found" errors

**Solution**:
- First run will download models (may take several minutes)
- Check worker logs for download progress
- Ensure sufficient disk space (models are several GB)

---

## Next Steps

1. **Explore the API**: Open http://localhost:8000/docs and try the interactive documentation

2. **Configure for Production**: Update `.env` with production settings

3. **Deploy to Cloud**: Follow the deployment guide in `README.md` for AWS or GCP

4. **Integrate Enhanced_AI**: Implement the Enhanced_AI service integration (see `FASTAPI_TRANSFORMATION_SUMMARY.md`)

5. **Set Up Monitoring**: Configure Prometheus and alerting

6. **Scale**: Add more workers and API instances as needed

---

## Additional Resources

- **Full Documentation**: See `fastapi_app/README.md`
- **Architecture**: See `ARCHITECTURE_DIAGRAMS.md`
- **Migration Guide**: See `FASTAPI_MIGRATION_PLAN.md`
- **API Reference**: http://localhost:8000/docs (when running)

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review documentation files
3. Verify environment configuration
4. Test with simple audio files first

Happy transcribing! 🎙️→📝
