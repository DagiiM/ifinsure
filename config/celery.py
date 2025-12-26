"""
Celery Configuration for iFinsure

This module configures Celery for background task processing.
"""
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Create Celery app
app = Celery('ifinsure')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Africa/Nairobi',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Beat scheduler
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
