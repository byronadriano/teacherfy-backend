import os
import logging
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from src.db import test_connection

# 1. Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 2. Load environment variables
load_dotenv()

# Development mode
DEVELOPMENT_MODE = os.environ.get("FLASK_ENV") == "development"

# Usage limits based on environment
if DEVELOPMENT_MODE:
    DAILY_GENERATION_LIMIT = 1000  # High limit for development
    DAILY_DOWNLOAD_LIMIT = 1000
else:
    DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", 3))
    DAILY_DOWNLOAD_LIMIT = int(os.environ.get("DAILY_DOWNLOAD_LIMIT", 1))

# 3. PostgreSQL Database Settings
# PostgreSQL Database Settings
POSTGRES_DB = os.environ.get("POSTGRES_DB", "teacherfy_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "bpulluta")  # Changed default
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "P!p!to031323!")  # Changed default
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "teacherfydb.postgres.database.azure.com")  # Changed default
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

# Create a dictionary for database configuration
DB_CONFIG = {
    'dbname': POSTGRES_DB,
    'user': POSTGRES_USER,
    'password': POSTGRES_PASSWORD,
    'host': POSTGRES_HOST,
    'port': POSTGRES_PORT,
    'sslmode': 'require'  # Required for Azure PostgreSQL
}

# Test database connection
if test_connection():
    logger.info("PostgreSQL database connection successful.")
else:
    logger.error("Failed to connect to PostgreSQL database!")

# 4. Google OAuth settings
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/oauth2callback" if DEVELOPMENT_MODE else None)
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

# Initialize OAuth flow
try:
    if CLIENT_ID and CLIENT_SECRET and REDIRECT_URI:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES
        )
    else:
        logger.warning("Google OAuth credentials are missing!")
        flow = None
except Exception as e:
    logger.error(f"Google OAuth initialization error: {e}")
    flow = None

# 5. Initialize OpenAI
try:
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("Missing OpenAI API key!")

    client = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized successfully.")
except Exception as e:
    logger.error(f"OpenAI initialization error: {e}")
    client = None