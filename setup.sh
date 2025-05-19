#!/bin/bash
# setup.sh - Consolidated setup script for Teacherfy backend
# This script combines functionality from:
# - setup_history.sh
# - setup_history_routes.sh
# - setup_migration.sh
# - setup_recents_list.sh
# - run_migration.sh

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}Teacherfy Backend Setup${NC}"
echo -e "${GREEN}=======================================${NC}\n"

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

# Function to run a setup task
run_task() {
    echo -e "\n${YELLOW}TASK: $1${NC}"
    shift
    if $@; then
        echo -e "${GREEN}✅ Task completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Task failed${NC}"
        return 1
    fi
}

# Check requirements
check_requirements() {
    local missing=0
    
    if ! command_exists python3; then
        echo -e "${RED}Python 3 is not installed. Please install Python 3.${NC}"
        missing=1
    fi
    
    if ! command_exists pip; then
        echo -e "${RED}pip is not installed. Please install pip.${NC}"
        missing=1
    fi
    
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Warning: .env file not found. Creating sample .env file...${NC}"
        cat > .env << EOL
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
POSTGRES_DB=teacherfy_db
POSTGRES_USER=teacherfy_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback
EOL
        echo -e "${YELLOW}Please update the .env file with your actual values.${NC}"
    fi
    
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}requirements.txt not found.${NC}"
        missing=1
    fi
    
    return $missing
}

# Install dependencies
install_dependencies() {
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
}

# Setup database migration structure
setup_migrations() {
    echo "Setting up migration directory structure..."
    mkdir -p src/db/migrations
    touch src/db/migrations/__init__.py
    
    # Copy migration script to the directory if it doesn't exist
    if [ ! -f "src/db/migrations/add_history_support.py" ]; then
        echo "Creating migration script..."
        cp src/db/migrations/add_history_support.py src/db/migrations/ 2>/dev/null || echo "Migration script already exists or source file not found."
    fi
}

# Run database migrations
run_migrations() {
    echo "Running database migrations..."
    python -m src.db.migrations.add_history_support
}

# Setup history routes
setup_history_routes() {
    echo "Setting up history routes..."
    
    # Check if history_blueprint is already imported in app.py
    if ! grep -q "from src.history_routes import history_blueprint" app.py; then
        # Add the import statement
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS requires empty string for -i
            sed -i '' 's/from src.db.database import test_connection/from src.db.database import test_connection\nfrom src.history_routes import history_blueprint  # Import the new blueprint/' app.py
            # Add the blueprint registration
            sed -i '' 's/app.register_blueprint(presentation_blueprint)/app.register_blueprint(presentation_blueprint)\n    app.register_blueprint(history_blueprint)  # Register the new blueprint/' app.py
        else
            # Linux version
            sed -i 's/from src.db.database import test_connection/from src.db.database import test_connection\nfrom src.history_routes import history_blueprint  # Import the new blueprint/' app.py
            # Add the blueprint registration
            sed -i 's/app.register_blueprint(presentation_blueprint)/app.register_blueprint(presentation_blueprint)\n    app.register_blueprint(history_blueprint)  # Register the new blueprint/' app.py
        fi
        echo "✅ app.py updated successfully!"
    else
        echo "✅ History blueprint already in app.py - no changes needed."
    fi
}

# Setup frontend components
setup_frontend_components() {
    echo "Setting up frontend components..."
    
    # Create frontend directories if they don't exist
    mkdir -p src/components/sidebar
    
    # Check if RecentsList component exists
    if [ ! -f "src/components/sidebar/RecentsList.jsx" ]; then
        echo "RecentsList component not found. This should be created manually."
    fi
}

# Main execution
main() {
    # Check requirements
    run_task "Checking requirements" check_requirements
    if [ $? -ne 0 ]; then
        echo -e "${RED}Please install missing requirements and try again.${NC}"
        exit 1
    fi
    
    # Ask which components to set up
    echo -e "\n${YELLOW}What would you like to set up?${NC}"
    echo "1) Full setup (all components)"
    echo "2) Database only"
    echo "3) History functionality only"
    echo "4) Frontend components only"
    echo "5) Exit"
    
    read -p "Enter your choice [1-5]: " choice
    
    case $choice in
        1)
            # Full setup
            run_task "Installing dependencies" install_dependencies
            run_task "Setting up migrations" setup_migrations
            run_task "Running migrations" run_migrations
            run_task "Setting up history routes" setup_history_routes
            run_task "Setting up frontend components" setup_frontend_components
            ;;
        2)
            # Database only
            run_task "Setting up migrations" setup_migrations
            run_task "Running migrations" run_migrations
            ;;
        3)
            # History functionality only
            run_task "Setting up migrations" setup_migrations
            run_task "Running migrations" run_migrations
            run_task "Setting up history routes" setup_history_routes
            ;;
        4)
            # Frontend components only
            run_task "Setting up frontend components" setup_frontend_components
            ;;
        5)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Exiting.${NC}"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}Setup completed!${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "\nYou can now start the development server with:"
    echo -e "  ${YELLOW}python run_dev.py${NC}"
    echo -e "\nOr use Gunicorn for production:"
    echo -e "  ${YELLOW}gunicorn --bind=0.0.0.0 --timeout 600 app:app${NC}"
}

# Run main function
main