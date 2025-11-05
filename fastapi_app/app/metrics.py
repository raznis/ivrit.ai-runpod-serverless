"""
Prometheus metrics for monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# Job metrics
jobs_submitted = Counter(
    'scribe_rabbit_jobs_submitted_total',
    'Total number of jobs submitted'
)

jobs_completed = Counter(
    'scribe_rabbit_jobs_completed_total',
    'Total number of jobs completed successfully'
)

jobs_failed = Counter(
    'scribe_rabbit_jobs_failed_total',
    'Total number of jobs that failed'
)

jobs_cancelled = Counter(
    'scribe_rabbit_jobs_cancelled_total',
    'Total number of jobs cancelled'
)

# Processing metrics
job_duration = Histogram(
    'scribe_rabbit_job_duration_seconds',
    'Job processing duration in seconds',
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

transcription_duration = Histogram(
    'scribe_rabbit_transcription_duration_seconds',
    'Transcription duration in seconds',
    buckets=[5, 10, 30, 60, 120, 300, 600]
)

# Queue metrics
queue_depth = Gauge(
    'scribe_rabbit_queue_depth',
    'Current number of jobs in queue'
)

active_workers = Gauge(
    'scribe_rabbit_active_workers',
    'Number of active worker processes'
)

# System info
app_info = Info(
    'scribe_rabbit_app',
    'Application information'
)


def init_metrics():
    """Initialize metrics with default values"""
    app_info.info({
        'version': '1.0.0',
        'service': 'scribe-rabbit-api'
    })
    logger.info("Metrics initialized")
