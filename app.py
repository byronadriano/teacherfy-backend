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
                    "http://localhost:3000",
                    "https://teacherfy.ai",
                    "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
                "supports_credentials": True,
                "max_age": 3600
            }
        },
        supports_credentials=True)

    # Session configuration
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None',
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=3600,
        SESSION_COOKIE_DOMAIN=None,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024
    )

    # Secret key configuration
    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not app.secret_key:
        raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(slides_blueprint)
    app.register_blueprint(presentation_blueprint)

    @app.before_request
    def check_db_connection():
        if request.method == 'OPTIONS':
            return '', 204
            
        if not test_connection():
            logger.error("Database connection failed")
            return {"error": "Database connection failed"}, 500

    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'https://teacherfy.ai',
            'https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net'
        ]
        
        if origin in allowed_origins:
            # Remove any existing CORS headers to prevent duplicates
            response.headers.pop('Access-Control-Allow-Origin', None)
            response.headers.pop('Access-Control-Allow-Credentials', None)
            
            # Set new CORS headers
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            
            if request.method == 'OPTIONS':
                response.headers['Access-Control-Max-Age'] = '3600'
        
        return response

    # Initialize example outlines
    with app.app_context():
        try:
            load_example_outlines()
            logger.info("Example outlines initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing example outlines: {e}")

    return app  # Added the return statement

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)