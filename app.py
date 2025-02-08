import os
from flask import Flask, request
from flask_cors import CORS
from src.config import logger
from src.auth_routes import auth_blueprint
from src.slides_routes import slides_blueprint
from src.presentation_routes import presentation_blueprint, load_example_outlines
from src.db.database import test_connection
import logging
from dotenv import load_dotenv

def create_app():
    # Initialize Flask app
    app = Flask(__name__)

    # Enhanced logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    # Load environment variables
    load_dotenv()

    # CORS configuration
    CORS(app, 
        resources={
            r"/*": {
                "origins": [
                    "https://teacherfy.ai",
                    "http://localhost:3000",
                    "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "Accept",
                    "Origin",
                    "Access-Control-Request-Method",
                    "Access-Control-Request-Headers"
                ],
                "supports_credentials": True,
                "expose_headers": [
                    "Content-Type", 
                    "Content-Disposition",
                    "Content-Length"
                ],
                "max_age": 3600
            }
        },
        supports_credentials=True)

    # Enhanced session configuration
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None',
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SESSION_COOKIE_DOMAIN=None,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max-limit
    )

    # Session configuration
    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not app.secret_key:
        raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

    # Database connection test before each request
    @app.before_request
    def check_db_connection():
        if request.method == 'OPTIONS':
            return '', 204
            
        if not test_connection():
            logger.error("Database connection failed")
            return {"error": "Database connection failed"}, 500

    # Initialize example outlines
    with app.app_context():
        try:
            load_example_outlines()
            logger.info("Example outlines initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing example outlines: {e}")

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(slides_blueprint)
    app.register_blueprint(presentation_blueprint)

    # Add OPTIONS method handlers for common routes
    @app.route('/outline', methods=['OPTIONS'])
    @app.route('/generate', methods=['OPTIONS'])
    @app.route('/generate_slides', methods=['OPTIONS'])
    def handle_options():
        return '', 204

    @app.after_request
    def after_request(response):
        # Get origin from request
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'https://teacherfy.ai',
            'https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net'
        ]
        
        # Set CORS headers if origin is allowed
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            
            # Handle PowerPoint downloads specifically
            if response.mimetype == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                response.headers.update({
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'Content-Disposition': 'attachment; filename=lesson_presentation.pptx',
                    'Access-Control-Expose-Headers': 'Content-Disposition, Content-Length'
                })
            
            # Set standard CORS headers
            response.headers.update({
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
                'Access-Control-Max-Age': '3600'
            })
            
            # For preflight requests
            if request.method == 'OPTIONS':
                response.headers.update({
                    'Access-Control-Max-Age': '3600',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
                })

        return response

    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)