import celery_healthcheck
from app.core.logging import configure_structlog
from app.tasks.presentation_tasks import celery_app  # noqa: F401

configure_structlog()

# Start health check HTTP server on port 9000 before the worker forks.
celery_healthcheck.start(port=9000)

# Celery worker entry point.
# Run with: celery -A celery_worker worker --loglevel=info
