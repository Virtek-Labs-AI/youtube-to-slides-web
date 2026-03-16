from app.tasks.presentation_tasks import celery_app

# Celery worker entry point.
# Run with: celery -A celery_worker.celery_app worker --loglevel=info
