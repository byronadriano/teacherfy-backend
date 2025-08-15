import os
from dotenv import load_dotenv

# Set Flask environment to development BEFORE importing anything from src
os.environ['FLASK_ENV'] = 'development'

from src.db.database import create_database_and_user, test_connection
from src.config import logger

def setup_development():
    # Load environment variables
    load_dotenv()
    
    # Test database connection
    if not test_connection():
        logger.info("Initial database connection failed, attempting to create database...")
        try:
            create_database_and_user()
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise

    logger.info("Database connection successful!")

if __name__ == "__main__":
    setup_development()
    
    # Import app after environment is set up
    from app import app
    
    # Run the app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)