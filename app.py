# app.py
import os
import tempfile
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from src.config import config, logger
from src.auth_routes import auth_blueprint
from src.slides_routes import slides_blueprint
from src.presentation_routes import presentation_blueprint, load_example_outlines
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
                "origins": config.CORS_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "Accept",
                    "Origin"
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
    app.register_blueprint(presentation_blueprint)
    
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

    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        
        if origin in config.CORS_ORIGINS:
            response.headers.update({
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control'
            })
            
            if response.mimetype == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                response.headers.update({
                    'Access-Control-Expose-Headers': 'Content-Disposition, Content-Type, Content-Length',
                    'Content-Disposition': 'attachment; filename=lesson_presentation.pptx',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                })
        
        return response

    # Initialize example outlines
    with app.app_context():
        try:
            load_example_outlines()
            logger.info("Example outlines initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing example outlines: {e}")

    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = config.DEVELOPMENT_MODE
    app.run(host="0.0.0.0", port=port, debug=debug_mode)