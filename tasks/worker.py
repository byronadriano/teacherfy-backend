# run_celery.py
from app import create_app
from background_tasks import init_celery

def create_celery_app():
    """Create Flask app and initialize Celery for worker"""
    flask_app = create_app()
    celery = init_celery(flask_app)
    return celery

# Create the celery app instance
celery_app = create_celery_app()

if __name__ == '__main__':
    # Run the celery worker
    # Use: python run_celery.py worker --loglevel=info
    # Or: celery -A run_celery:celery_app worker --loglevel=info
    celery_app.start()