# celery_config.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def make_celery(app):
    """Create and configure Celery instance"""
    
    # Configure Redis URL for Azure or local development
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # If Azure Redis URL format, convert it to proper redis:// format
    if 'redis.cache.windows.net' in redis_url:
        # Parse Azure Redis connection string: host:port,password=xxx,ssl=True,abortConnect=False
        parts = redis_url.split(',')
        host_port = parts[0]
        password = None
        ssl_required = False
        
        for part in parts[1:]:
            if part.startswith('password='):
                password = part.split('=', 1)[1]
            elif part.startswith('ssl=True'):
                ssl_required = True
        
        if ssl_required and password:
            # Use rediss:// for SSL connections with proper SSL parameters
            # For production, use CERT_REQUIRED for security
            ssl_cert_reqs = os.getenv('REDIS_SSL_CERT_REQS', 'CERT_NONE')
            redis_url = f"rediss://default:{password}@{host_port}/0?ssl_cert_reqs={ssl_cert_reqs}"
        elif password:
            redis_url = f"redis://default:{password}@{host_port}/0"
        else:
            redis_url = f"redis://{host_port}/0"
        
        print(f"Converted Azure Redis URL to: {redis_url.replace(password, '***') if password else redis_url}")
    
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url,
        include=['tasks.jobs']  # Include your background tasks module
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