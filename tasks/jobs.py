# background_tasks.py
import os
import time
import json
import traceback
from config.celery_config import make_celery
from core.services.email_service import email_service
from flask import current_app
import logging

logger = logging.getLogger(__name__)

# This will be initialized when Flask app starts
celery = None

def init_celery(app):
    """Initialize Celery with Flask app"""
    global celery
    celery = make_celery(app)
    # Register tasks with the celery instance
    register_tasks(celery)
    return celery

def register_tasks(celery_instance):
    """Register tasks with the given celery instance"""
    
    @celery_instance.task(bind=True, name='generate_resources_background')
    def generate_resources_background(self, job_data):
        """
        Background task for resource generation
        
        Expected job_data structure:
        {
            'job_id': 'unique_job_id',
            'operation_type': 'outline_generation' or 'resource_generation',
            'notification_email': 'user@example.com',
            'resource_types': ['Presentation', 'Worksheet'],
            'structured_content': [...],
            'grade_level': '5th Grade',
            'subject': 'Math',
            'topic': 'Fractions',
            'include_images': False,
            # ... other form data
        }
        """
        job_id = job_data.get('job_id')
        notification_email = job_data.get('notification_email')
        resource_types = job_data.get('resource_types', ['Presentation'])

        try:
            logger.info(f"Starting background job {job_id}")

            # Update job status to 'processing'
            self.update_state(
                state='PROCESSING',
                meta={
                    'job_id': job_id,
                    'status': 'processing',
                    'progress': 10,
                    'message': 'Starting resource generation...',
                    'started_at': time.time()
                }
            )

            # Step 1: Analyze requirements (simulate progress)
            time.sleep(2)
            self.update_state(
                state='PROCESSING',
                meta={
                    'job_id': job_id,
                    'status': 'processing',
                    'progress': 25,
                    'message': 'Analyzing content requirements...',
                }
            )

            # Step 2: Generate content (this is where you'd call your existing generation logic)
            result = perform_actual_generation(job_data, self)

            # Step 3: Finalize and prepare download
            self.update_state(
                state='PROCESSING',
                meta={
                    'job_id': job_id,
                    'status': 'processing',
                    'progress': 90,
                    'message': 'Finalizing resources...',
                }
            )

            time.sleep(1)

            # Step 4: Complete and send notification
            download_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/download/{job_id}"

            # Send success email
            if notification_email:
                email_service.send_job_completion_email(
                    to_email=notification_email,
                    job_id=job_id,
                    resource_types=resource_types,
                    download_url=download_url
                )

            logger.info(f"Background job {job_id} completed successfully")

            return {
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'message': 'Resources generated successfully',
                'download_url': download_url,
                'result': result,
                'completed_at': time.time()
            }

        except Exception as e:
            error_message = str(e)
            logger.error(f"Background job {job_id} failed: {error_message}")
            logger.error(traceback.format_exc())

            # Send error email
            if notification_email:
                email_service.send_job_completion_email(
                    to_email=notification_email,
                    job_id=job_id,
                    resource_types=resource_types,
                    error=error_message
                )

            # Update job status to failed
            self.update_state(
                state='FAILURE',
                meta={
                    'job_id': job_id,
                    'status': 'failed',
                    'error': error_message,
                    'failed_at': time.time()
                }
            )

            raise

    return generate_resources_background

def perform_actual_generation(job_data, task_instance):
    """
    Integrate with your existing resource generation logic
    This calls your current presentation generation functions
    """
    try:
        # Import your existing services here
        from resources.types import get_resource_handler
        
        resource_types = job_data.get('resource_types', ['Presentation'])
        structured_content = job_data.get('structured_content', [])
        include_images = job_data.get('include_images', False)
        results = {}

        total_resources = len(resource_types)
        base_progress = 25  # Starting progress
        progress_per_resource = 60 / total_resources  # 60% for generation (25% to 85%)

        for i, resource_type in enumerate(resource_types):
            current_progress = base_progress + (i * progress_per_resource)

            task_instance.update_state(
                state='PROCESSING',
                meta={
                    'job_id': job_data.get('job_id'),
                    'status': 'processing',
                    'progress': int(current_progress),
                    'message': f'Generating {resource_type}...',
                }
            )

            # Normalize resource type to match your existing system
            normalized_resource_type = resource_type.lower().replace('-', '_').replace(' ', '_')
            
            # Map to handler types as per your existing logic
            if "quiz" in normalized_resource_type or "test" in normalized_resource_type:
                handler_type = "quiz"
            elif "lesson" in normalized_resource_type and "plan" in normalized_resource_type:
                handler_type = "lesson_plan"
            elif "worksheet" in normalized_resource_type or "activity" in normalized_resource_type:
                handler_type = "worksheet"
            else:
                handler_type = "presentation"  # Default

            logger.info(f"Generating {handler_type} for job {job_data.get('job_id')}")

            # Create the handler instance with your existing system
            handler = get_resource_handler(handler_type, structured_content, include_images=include_images)
            
            # Generate the resource
            file_path = handler.generate()
            
            # Store result with file path
            results[resource_type] = {
                "type": handler_type, 
                "file_path": file_path,
                "generated_at": time.time()
            }

            logger.info(f"Successfully generated {handler_type} at {file_path}")

        return results

    except Exception as e:
        logger.error(f"Error in actual generation: {str(e)}")
        logger.error(traceback.format_exc())
        raise