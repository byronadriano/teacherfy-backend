# src/config.py - CLEANED VERSION
import os
import logging
from typing import Dict, Any, List
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

class BaseConfig:
    """Base configuration class with shared settings."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Set environment mode
        self.DEVELOPMENT_MODE = os.environ.get("FLASK_ENV") == "development"
        
        # Configure logging
        self._setup_logging()
        
        # Set OAuth credentials
        self.CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
        self.CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
        
        # Environment-aware redirect URI
        if self.DEVELOPMENT_MODE:
            self.REDIRECT_URI = "http://localhost:5000/oauth2callback"
        else:
            self.REDIRECT_URI = "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net/oauth2callback"
        
        # Initialize external services
        self.deepseek_client = self._init_deepseek()
        self.oauth_flow = self._init_oauth()

    def _setup_logging(self) -> None:
        """Configure logging settings with Azure compatibility."""
        import sys
        import tempfile
        
        # Determine log file location
        if self.DEVELOPMENT_MODE:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "app.log")
        else:
            log_path = os.path.join(tempfile.gettempdir(), "app.log")

        try:
            handlers = [logging.StreamHandler(sys.stdout)]
            
            # Try to add file handler if possible
            try:
                file_handler = logging.FileHandler(log_path)
                handlers.append(file_handler)
            except Exception as e:
                print(f"Warning: Could not create log file at {log_path}: {e}")

            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Logging initialized. Environment: {'Development' if self.DEVELOPMENT_MODE else 'Production'}")
            
        except Exception as e:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Failed to initialize logging: {str(e)}. Falling back to console logging only.")

    def _init_deepseek(self) -> OpenAI:
        """Initialize DeepSeek client using OpenAI SDK."""
        try:
            deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
            
            if not deepseek_api_key:
                raise ValueError("Missing DEEPSEEK_API_KEY environment variable!")
            
            client = OpenAI(
                api_key=deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            
            self.logger.info("DeepSeek client initialized successfully.")
            return client
            
        except Exception as e:
            self.logger.error(f"DeepSeek initialization error: {e}")
            return None

    def _init_oauth(self) -> Flow:
        """Initialize Google OAuth flow."""
        try:
            if not all([self.CLIENT_ID, self.CLIENT_SECRET, self.REDIRECT_URI]):
                missing = []
                if not self.CLIENT_ID: missing.append("CLIENT_ID")
                if not self.CLIENT_SECRET: missing.append("CLIENT_SECRET") 
                if not self.REDIRECT_URI: missing.append("REDIRECT_URI")
                
                self.logger.error(f"Missing OAuth credentials: {missing}")
                return None

            oauth_config = {
                "web": {
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "redirect_uris": [self.REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
            
            flow = Flow.from_client_config(oauth_config, scopes=SCOPES)
            flow.redirect_uri = self.REDIRECT_URI
            
            # Ensure proper HTTPS in production
            if not self.DEVELOPMENT_MODE:
                if 'OAUTHLIB_INSECURE_TRANSPORT' in os.environ:
                    del os.environ['OAUTHLIB_INSECURE_TRANSPORT']
                    self.logger.info("Removed OAUTHLIB_INSECURE_TRANSPORT for production")
            
            self.logger.info("OAuth flow created successfully")
            return flow
            
        except Exception as e:
            self.logger.error(f"Google OAuth initialization error: {e}")
            return None
    
    # Common settings
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400 * 30  # 30 days
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_NAME = 'teacherfy_session'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @property
    def DB_CONFIG(self) -> Dict[str, Any]:
        """Database configuration."""
        return {
            'dbname': os.environ.get("POSTGRES_DB", "teacherfy_db"),
            'user': os.environ.get("POSTGRES_USER", "bpulluta"),
            'password': os.environ.get("POSTGRES_PASSWORD", "P!p!to031323!"),
            'host': os.environ.get("POSTGRES_HOST", "teacherfydb.postgres.database.azure.com"),
            'port': os.environ.get("POSTGRES_PORT", "5432"),
            'sslmode': 'require'
        }

class DevelopmentConfig(BaseConfig):
    """Development-specific configuration."""
    
    def __init__(self):
        super().__init__()
        # Development session settings
        self.SESSION_COOKIE_SECURE = False
        self.SESSION_COOKIE_SAMESITE = 'Lax'
        
        # Development CORS origins
        self.CORS_ORIGINS = ["http://localhost:3000", "*"]

class ProductionConfig(BaseConfig):
    """Production-specific configuration."""
    
    def __init__(self):
        super().__init__()
        # Production session settings
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_SAMESITE = 'None'
        
        # Production CORS origins
        self.CORS_ORIGINS = [
            "https://teacherfy.ai",
            "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
        ]

def get_config():
    """Get the appropriate configuration based on environment."""
    if os.environ.get("FLASK_ENV") == "development":
        return DevelopmentConfig()
    return ProductionConfig()

# Instantiate config
config = get_config()

# Export commonly used instances and settings
logger = config.logger
client = config.deepseek_client  # This is the DeepSeek client
flow = config.oauth_flow
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI

# Test database connection on startup
def test_db_on_startup():
    """Test database connection on startup."""
    try:
        from src.db.database import test_connection
        if test_connection():
            logger.info("✅ PostgreSQL database connection successful.")
            return True
        else:
            logger.error("❌ Failed to connect to PostgreSQL database!")
            return False
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

# Initialize database connection test
if __name__ != "__main__":
    test_db_on_startup()