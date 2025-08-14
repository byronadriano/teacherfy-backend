# app.py - FIXED VERSION with COOP headers and background job processing
import os
import tempfile
import uuid
import time
import re
from datetime import timedelta
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from src.config import config, logger
from src.auth_routes import auth_blueprint
from src.slides_routes import slides_blueprint
from src.outline_routes import outline_blueprint
from src.history_routes import history_blueprint
from src.resource_routes import resource_blueprint
from src.db.database import test_connection

def create_app():
    # Initialize Flask app
    app = Flask(__name__)

    # Apply configuration from config object
    app.config.update(
        # Session security
        SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_SAMESITE=config.SESSION_COOKIE_SAMESITE,
        SESSION_COOKIE_HTTPONLY=config.SESSION_COOKIE_HTTPONLY,
        SESSION_PERMANENT=config.SESSION_PERMANENT,
        PERMANENT_SESSION_LIFETIME=config.PERMANENT_SESSION_LIFETIME,
        SESSION_COOKIE_DOMAIN=config.SESSION_COOKIE_DOMAIN,
        SESSION_COOKIE_NAME=config.SESSION_COOKIE_NAME,
        MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
        
        # Secret key
        SECRET_KEY=config.SECRET_KEY
    )

    # CORS configuration
    CORS(app, 
        resources={
            r"/*": {
                "origins": ["http://localhost:3000", "https://teacherfy.ai", "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net", "*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "Accept",
                    "Origin",
                    "Cache-Control"
                ],
                "supports_credentials": True,
                "expose_headers": [
                    "Content-Disposition",
                    "Content-Type", 
                    "Content-Length",
                    "Authorization",
                    "Set-Cookie"
                ]
            }
        },
        supports_credentials=True)

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(slides_blueprint)
    app.register_blueprint(outline_blueprint)
    app.register_blueprint(history_blueprint)
    app.register_blueprint(resource_blueprint)

    # Initialize Celery for background jobs
    try:
        # First check if celery package is available
        import celery as celery_package
        
        from celery_config import make_celery
        from background_tasks import init_celery
        from email_service import email_service
        
        celery = init_celery(app)
        generate_resources_background = celery.tasks.get('generate_resources_background')
        
        # In-memory job storage (use Redis or database in production)
        job_storage = {}
        
        logger.info("Celery initialized successfully for background job processing")
    except ImportError as e:
        logger.warning(f"Celery not available, background jobs disabled: {e}")
        celery = None
        generate_resources_background = None
        job_storage = {}
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {e}")
        celery = None
        generate_resources_background = None
        job_storage = {}

    # Background job endpoints
    @app.route('/generate/background', methods=['POST'])
    def start_background_generation():
        """Start background resource generation job"""
        if celery is None:
            return jsonify({'error': 'Background job processing not available'}), 503
            
        try:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No data provided'}), 400

            # Validate required fields
            required_fields = ['structured_content']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            # Generate unique job ID
            job_id = data.get('job_id', f"job_{int(time.time())}_{str(uuid.uuid4())[:8]}")

            # Prepare job data
            job_data = {
                'job_id': job_id,
                'operation_type': data.get('operation_type', 'resource_generation'),
                'notification_email': data.get('notification_email'),
                'resource_types': data.get('resource_types', ['Presentation']),
                'structured_content': data.get('structured_content'),
                'grade_level': data.get('grade_level'),
                'subject': data.get('subject'),
                'topic': data.get('topic'),
                'include_images': data.get('include_images', False),
                'background_mode': True,
                'started_at': time.time()
            }

            # Validate email if provided
            email = job_data.get('notification_email')
            if email and not _is_valid_email(email):
                return jsonify({'error': 'Invalid email address'}), 400

            # Start the background task
            if generate_resources_background is None:
                return jsonify({'error': 'Background task not available'}), 503
            task = generate_resources_background.delay(job_data)

            # Store job info
            job_storage[job_id] = {
                'task_id': task.id,
                'status': 'queued',
                'progress': 0,
                'message': 'Job queued successfully',
                'started_at': time.time(),
                'job_data': job_data
            }

            logger.info(f"Started background job {job_id} with task ID {task.id}")

            return jsonify({
                'job_id': job_id,
                'task_id': task.id,
                'status': 'queued',
                'progress': 0,
                'message': 'Background job started successfully',
                'estimated_duration': _estimate_duration(job_data)
            }), 200

        except Exception as e:
            logger.error(f"Error starting background job: {str(e)}")
            return jsonify({'error': f'Failed to start background job: {str(e)}'}), 500

    @app.route('/generate/status/<job_id>', methods=['GET'])
    def get_job_status(job_id):
        """Get the status of a background job"""
        if celery is None:
            return jsonify({'error': 'Background job processing not available'}), 503
            
        try:
            if job_id not in job_storage:
                return jsonify({'error': 'Job not found'}), 404

            job_info = job_storage[job_id]
            task_id = job_info['task_id']

            # Get task status from Celery
            if generate_resources_background is None:
                return jsonify({'error': 'Background task not available'}), 503
            task = generate_resources_background.AsyncResult(task_id)

            if task.state == 'PENDING':
                response = {
                    'job_id': job_id,
                    'status': 'queued',
                    'progress': 0,
                    'message': 'Job is queued'
                }
            elif task.state == 'PROCESSING':
                response = {
                    'job_id': job_id,
                    'status': 'processing',
                    'progress': task.info.get('progress', 0),
                    'message': task.info.get('message', 'Processing...')
                }
            elif task.state == 'SUCCESS':
                result = task.result
                response = {
                    'job_id': job_id,
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Job completed successfully',
                    'download_url': result.get('download_url'),
                    'result': result.get('result')
                }
            elif task.state == 'FAILURE':
                response = {
                    'job_id': job_id,
                    'status': 'failed',
                    'progress': 0,
                    'message': f'Job failed: {str(task.info)}',
                    'error': str(task.info)
                }
            else:
                response = {
                    'job_id': job_id,
                    'status': task.state.lower(),
                    'progress': 0,
                    'message': f'Job status: {task.state}'
                }

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {str(e)}")
            return jsonify({'error': f'Failed to get job status: {str(e)}'}), 500

    @app.route('/generate/cancel/<job_id>', methods=['POST'])
    def cancel_job(job_id):
        """Cancel a background job"""
        if celery is None:
            return jsonify({'error': 'Background job processing not available'}), 503
            
        try:
            if job_id not in job_storage:
                return jsonify({'error': 'Job not found'}), 404

            job_info = job_storage[job_id]
            task_id = job_info['task_id']

            # Revoke the task
            celery.control.revoke(task_id, terminate=True)

            # Update job status
            job_storage[job_id]['status'] = 'cancelled'

            logger.info(f"Cancelled job {job_id}")

            return jsonify({
                'job_id': job_id,
                'status': 'cancelled',
                'message': 'Job cancelled successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {str(e)}")
            return jsonify({'error': f'Failed to cancel job: {str(e)}'}), 500

    @app.route('/outline/background', methods=['POST'])
    def start_background_outline():
        """Start background outline generation (same as resource generation but different endpoint)"""
        return start_background_generation()

    def _is_valid_email(email):
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _estimate_duration(job_data):
        """Estimate job duration based on complexity"""
        resource_count = len(job_data.get('resource_types', ['Presentation']))
        content_length = len(job_data.get('structured_content', []))

        if resource_count == 1:
            base_time = 45
            complexity_factor = min(content_length * 3, 45)
            return base_time + complexity_factor
        else:
            research_time = 30
            per_resource_time = 80
            complexity_multiplier = max(1, content_length / 10)
            total_time = research_time + (resource_count * per_resource_time * complexity_multiplier)
            return min(total_time, 480)

    @app.after_request
    def after_request(response):
        # Get the origin from the request
        origin = request.headers.get('Origin', '*')
        allowed_origins = config.CORS_ORIGINS + ['http://localhost:3000']
        
        # If the origin is allowed, set CORS headers
        if origin in allowed_origins or '*' in allowed_origins:
            response.headers.update({
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control',
            })
            
            # FIXED: Add COOP headers for OAuth pages
            # Allow popups to communicate with parent window during OAuth
            if request.endpoint in ['auth_blueprint.oauth2callback', 'auth_blueprint.authorize']:
                response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
                response.headers['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
            else:
                # For other pages, use safer defaults
                response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
            
            # For file downloads, add additional headers - now handles multiple MIME types
            if response.mimetype in [
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/pdf'
            ]:
                file_ext = '.pptx'
                if response.mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                    file_ext = '.docx'
                elif response.mimetype == 'application/pdf':
                    file_ext = '.pdf'
                    
                response.headers.update({
                    'Access-Control-Expose-Headers': 'Content-Disposition, Content-Type, Content-Length',
                    'Content-Disposition': f'attachment; filename=lesson_resource{file_ext}',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                })
        
        return response
    
    @app.route("/health")
    def health_check():
        try:
            # Test database connection
            db_status = test_connection()
            
            # Test file system
            temp_dir = tempfile.gettempdir()
            fs_writable = os.access(temp_dir, os.W_OK)
            
            return jsonify({
                "status": "healthy" if all([db_status, fs_writable]) else "unhealthy",
                "checks": {
                    "database": db_status,
                    "filesystem": fs_writable,
                },
                "version": "1.0.0",
                "environment": os.environ.get("FLASK_ENV", "production")
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500
            
    @app.route('/debug/database')
    def debug_database():
        """Test database operations directly"""
        from src.db import get_user_by_email, create_user, log_user_login
        
        test_results = {}
        
        try:
            # Test 1: Check if database connection works
            from src.db.database import test_connection
            test_results['connection'] = test_connection()
            
            # Test 2: Try to get a user (should return None if no user exists)
            test_email = "test@example.com"
            existing_user = get_user_by_email(test_email)
            test_results['existing_user'] = existing_user
            
            # Test 3: Try to create a test user
            try:
                user_id = create_user(test_email, "Test User", "https://example.com/pic.jpg")
                test_results['create_user_success'] = True
                test_results['created_user_id'] = user_id
                
                # Test 4: Try to log login for the test user
                try:
                    log_user_login(user_id)
                    test_results['log_login_success'] = True
                except Exception as e:
                    test_results['log_login_error'] = str(e)
                    
            except Exception as e:
                test_results['create_user_error'] = str(e)
            
            # Test 5: Check if user now exists
            final_user = get_user_by_email(test_email)
            test_results['final_user'] = final_user
            
        except Exception as e:
            test_results['general_error'] = str(e)
            import traceback
            test_results['traceback'] = traceback.format_exc()
        
        return test_results

    @app.route('/debug/session')
    def debug_session():
        """Debug route to check session contents"""
        from flask import session
        return {
            'session_keys': list(session.keys()),
            'has_credentials': 'credentials' in session,
            'has_user_info': 'user_info' in session,
            'session_id': request.cookies.get('session'),
            'development_mode': config.DEVELOPMENT_MODE,
            'redirect_uri': config.REDIRECT_URI,
            'session_contents': dict(session) if session else {}
        }
            
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            origin = request.headers.get('Origin')
            
            if origin in config.CORS_ORIGINS:
                response.headers.update({
                    'Access-Control-Allow-Origin': origin,
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control',
                    'Access-Control-Allow-Credentials': 'true',
                    'Access-Control-Max-Age': '3600',
                    'Access-Control-Expose-Headers': 'Content-Disposition, Content-Type, Content-Length'
                })
            return response, 204

    @app.before_request
    def check_db_connection():
        if request.method == 'OPTIONS':
            return None
            
        if not test_connection():
            logger.error("Database connection failed")
            return {"error": "Database connection failed"}, 500
        return None

    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = config.DEVELOPMENT_MODE
    app.run(host="0.0.0.0", port=port, debug=debug_mode)