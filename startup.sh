#!/bin/bash
# startup.sh - Consolidated startup script for Teacherfy backend
# This script combines functionality from:
# - run_dev.py
# - startup.sh
# - startup.txt
# 
# Usage: ./startup.sh [dev|prod]

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default mode is development
MODE=${1:-dev}

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}Teacherfy Backend Startup${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for requirements
check_requirements() {
    local missing=0
    
    if [ "$MODE" = "dev" ]; then
        if ! command_exists python3; then
            echo -e "${RED}Python 3 is not installed. Please install Python 3.${NC}"
            missing=1
        fi
    else
        if ! command_exists gunicorn; then
            echo -e "${RED}Gunicorn is not installed. Please install gunicorn using:${NC}"
            echo "pip install gunicorn"
            missing=1
        fi
    fi
    
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Warning: .env file not found. Some environment variables might be missing.${NC}"
        echo -e "${YELLOW}Creating a sample .env file...${NC}"
        cat > .env << EOL
FLASK_ENV=${MODE}
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
POSTGRES_DB=teacherfy_db
POSTGRES_USER=teacherfy_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback
MONTHLY_GENERATION_LIMIT=15
MONTHLY_DOWNLOAD_LIMIT=15
PORT=5000
EOL
        echo -e "${YELLOW}Please update the .env file with your actual values.${NC}"
    fi
    
    return $missing
}

# Check if the database is ready
check_database() {
    echo -e "${YELLOW}Testing database connection...${NC}"
    python -c "from dotenv import load_dotenv; load_dotenv(); from src.db.database import test_connection; print('Database connection ' + ('successful' if test_connection() else 'failed'));" || echo -e "${RED}Database connection test failed${NC}"
}

# Start the development server
start_dev_server() {
    echo -e "${GREEN}Starting development server...${NC}"
    export FLASK_ENV=development
    python run_dev.py
}

# Start the production server
start_prod_server() {
    echo -e "${GREEN}Starting production server with Gunicorn...${NC}"
    
    # Get port from environment or use default
    PORT=${PORT:-5000}
    
    # Set number of workers based on CPU cores
    if command_exists nproc; then
        WORKERS=$(($(nproc) * 2 + 1))
    else
        WORKERS=4  # Default if we can't determine CPU count
    fi
    
    echo -e "${YELLOW}Using $WORKERS workers on port $PORT${NC}"
    
    # Start Gunicorn
    gunicorn --bind=0.0.0.0:$PORT \
        --workers=$WORKERS \
        --timeout=600 \
        --log-level=info \
        --access-logfile=- \
        --error-logfile=- \
        app:app
}

# Main startup function
main() {
    # Print startup mode
    if [ "$MODE" = "dev" ]; then
        echo -e "${GREEN}Starting in DEVELOPMENT mode${NC}"
    else
        echo -e "${GREEN}Starting in PRODUCTION mode${NC}"
    fi
    
    # Check requirements
    check_requirements
    if [ $? -ne 0 ]; then
        echo -e "${RED}Please install missing requirements and try again.${NC}"
        exit 1
    fi
    
    # Check database
    check_database
    
    # Start the appropriate server
    if [ "$MODE" = "dev" ]; then
        start_dev_server
    else
        start_prod_server
    fi
}

# Handle command line arguments
if [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "Usage: $0 [dev|prod]"
    echo
    echo -e "Options:"
    echo -e "  dev   Start in development mode (default)"
    echo -e "  prod  Start in production mode with Gunicorn"
    echo -e "  help  Show this help message"
    exit 0
elif [ "$1" != "dev" ] && [ "$1" != "prod" ] && [ "$1" != "" ]; then
    echo -e "${RED}Invalid mode: $1${NC}"
    echo -e "Valid modes: dev, prod"
    exit 1
fi

# Run the main function
main