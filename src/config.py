# src/config.py
import os
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from src.db import test_connection

# Define OAuth scopes at module level
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

class BaseConfig:
    """Base configuration class with shared settings."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configure logging
        self._setup_logging()
        
        # Set OAuth credentials
        self.CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
        self.CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
        self.REDIRECT_URI = os.environ.get(
            "GOOGLE_REDIRECT_URI", 
            "http://localhost:5000/oauth2callback" if self.DEVELOPMENT_MODE else None
        )
        
        # Initialize external services
        self.openai_client = self._init_openai()
        self.oauth_flow = self._init_oauth()

    def _setup_logging(self) -> None:
        """Configure logging settings with Azure compatibility."""
        import sys
        import tempfile
        
        # Determine log file location
        if self.DEVELOPMENT_MODE:
            # In development, use local logs directory
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "app.log")
        else:
            # In Azure/production, use temp directory
            log_path = os.path.join(tempfile.gettempdir(), "app.log")

        try:
            # Configure root logger
            handlers = [
                # Always log to stdout for Azure logging
                logging.StreamHandler(sys.stdout)
            ]
            
            # Try to add file handler if possible
            try:
                file_handler = logging.FileHandler(log_path)
                handlers.append(file_handler)
            except Exception as e:
                print(f"Warning: Could not create log file at {log_path}: {e}")

            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            
            # Set up this class's logger
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Logging initialized. Log file: {log_path if len(handlers) > 1 else 'stdout only'}")
            
            # Log some diagnostic information
            self.logger.info(f"Environment: {'Development' if self.DEVELOPMENT_MODE else 'Production'}")
            self.logger.info(f"Temp directory: {tempfile.gettempdir()}")
            
        except Exception as e:
            # Fallback to basic console logging if something goes wrong
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Failed to initialize logging: {str(e)}. Falling back to console logging only.")

    def _init_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client."""
        try:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("Missing OpenAI API key!")
            
            client = OpenAI(api_key=openai_api_key)
            self.logger.info("OpenAI client initialized successfully.")
            return client
        except Exception as e:
            self.logger.error(f"OpenAI initialization error: {e}")
            return None

    def _init_oauth(self) -> Optional[Flow]:
        """Initialize Google OAuth flow."""
        try:
            if not all([self.CLIENT_ID, self.CLIENT_SECRET, self.REDIRECT_URI]):
                self.logger.warning("Google OAuth credentials are missing!")
                return None

            return Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.CLIENT_ID,
                        "client_secret": self.CLIENT_SECRET,
                        "redirect_uris": [self.REDIRECT_URI],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=SCOPES
            )
        except Exception as e:
            self.logger.error(f"Google OAuth initialization error: {e}")
            return None

    # Common settings
    DEVELOPMENT_MODE = os.environ.get("FLASK_ENV") == "development"
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    
    # Session settings
    SESSION_COOKIE_SECURE = not DEVELOPMENT_MODE
    SESSION_COOKIE_SAMESITE = 'Lax' if DEVELOPMENT_MODE else 'None'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600
    SESSION_COOKIE_DOMAIN = None
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Database settings
    @property
    def DB_CONFIG(self) -> Dict[str, Any]:
        return {
            'dbname': os.environ.get("POSTGRES_DB", "teacherfy_db"),
            'user': os.environ.get("POSTGRES_USER"),
            'password': os.environ.get("POSTGRES_PASSWORD"),
            'host': os.environ.get("POSTGRES_HOST"),
            'port': os.environ.get("POSTGRES_PORT", "5432"),
            'sslmode': 'require'
        }

class DevelopmentConfig(BaseConfig):
    """Development-specific configuration."""
    
    DAILY_GENERATION_LIMIT = 1000
    DAILY_DOWNLOAD_LIMIT = 1000
    
    CORS_ORIGINS = ["http://localhost:3000"]
    
    # Override session settings for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    
class ProductionConfig(BaseConfig):
    """Production-specific configuration."""
    
    DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", 5))
    DAILY_DOWNLOAD_LIMIT = int(os.environ.get("DAILY_DOWNLOAD_LIMIT", 5))
    
    CORS_ORIGINS = [
        "https://teacherfy.ai",
        "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
    ]
    @property
    def handle_error(self, error):
        self.logger.error(f"Production error: {str(error)}", exc_info=True)
        return {"error": "Internal server error"}, 500
    # Override session settings for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'

def get_config():
    """Get the appropriate configuration based on environment."""
    if os.environ.get("FLASK_ENV") == "development":
        return DevelopmentConfig()
    return ProductionConfig()

# Instantiate config
config = get_config()

# Export commonly used instances and settings
logger = config.logger
client = config.openai_client
flow = config.oauth_flow
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI

# Verify database connection
if test_connection():
    logger.info("PostgreSQL database connection successful.")
else:
    logger.error("Failed to connect to PostgreSQL database!")