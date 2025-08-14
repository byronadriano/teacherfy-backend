# celery_config.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def make_celery(app):
    """Create and configure Celery instance"""
    celery = Celery(
        app.import_name,
        backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        include=['background_tasks']  # Include your background tasks module
    )

    # Update configuration with Flask app's config
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes max per task
        task_soft_time_limit=25 * 60,  # 25 minutes soft limit
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )

    # Make celery work with Flask application context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery