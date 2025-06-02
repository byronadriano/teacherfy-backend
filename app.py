# app.py - FIXED VERSION with COOP headers
import os
import tempfile
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
        PERMANENT_SESSION_LIFETIME=config.PERMANENT_SESSION_LIFETIME,
        SESSION_COOKIE_DOMAIN=config.SESSION_COOKIE_DOMAIN,
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
                    "Authorization"
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