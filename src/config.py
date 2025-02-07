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

# 3. PostgreSQL Database Settings
POSTGRES_DB = os.environ.get("POSTGRES_DB", "teacherfy_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "teacherfy_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "132392")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

# Test database connection
if test_connection():
    logger.info("PostgreSQL database connection successful.")
else:
    logger.error("Failed to connect to PostgreSQL database!")

# 4. Google OAuth settings
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
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