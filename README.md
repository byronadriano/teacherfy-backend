# Teacherfy Backend

## Overview

Teacherfy is an AI-powered platform for creating educational content, including presentations, lesson plans, worksheets, and quizzes. This repository contains the backend service built with Flask and PostgreSQL.

## Consolidated Scripts

To simplify maintenance, we've consolidated several scripts into a few key files:

### `setup.sh` - Setup & Configuration

This script handles all setup and configuration tasks, including:
- Database setup and migrations
- History functionality setup
- Frontend component configuration

**Usage:**
```bash
# Run with default options (interactive menu)
./setup.sh

# Make executable if needed
chmod +x setup.sh
```

### `test.sh` - Testing

This script provides comprehensive testing capabilities:
- Database connection testing
- API endpoint testing
- Rate limit testing

**Usage:**
```bash
# Run with default options (interactive menu)
./test.sh

# Make executable if needed
chmod +x test.sh
```

### `startup.sh` - Server Startup

This script handles starting the server in either development or production mode:
- Development mode using Flask's development server
- Production mode using Gunicorn

**Usage:**
```bash
# Development mode (default)
./startup.sh dev

# Production mode
./startup.sh prod

# Make executable if needed
chmod +x startup.sh
```

### `cleanup.sh` - File Cleanup

This script helps you clean up unnecessary files:
- Removes redundant scripts that have been consolidated
- Cleans up temporary files and caches
- Creates backups of important files before removal

**Usage:**
```bash
# Run with default options (interactive menu)
./cleanup.sh

# Make executable if needed
chmod +x cleanup.sh
```

## Project Structure

```
teacherfy-backend/
├── app.py                   # Main Flask application
├── run_dev.py               # Development server entry point
├── setup.sh                 # Consolidated setup script
├── startup.sh               # Consolidated startup script
├── test.sh                  # Consolidated test script
├── cleanup.sh               # Cleanup utility
├── requirements.txt         # Python dependencies
├── src/                     # Main source code
│   ├── auth_routes.py       # Authentication routes
│   ├── config.py            # Configuration settings
│   ├── history_routes.py    # History management routes
│   ├── presentation_routes.py # Presentation generation routes
│   ├── resource_routes.py   # General resource routes
│   ├── resource_types.py    # Resource type definitions
│   ├── slide_processor.py   # Slide processing utilities
│   ├── db/                  # Database modules
│   │   ├── database.py      # Database connection and utilities
│   │   ├── migrations/      # Database migrations
│   │   ├── schema.sql       # Database schema
│   │   └── usage.py         # Usage tracking
│   ├── resource_handlers/   # Resource generation handlers
│   │   ├── base_handler.py  # Base resource handler
│   │   ├── presentation_handler.py # Presentation generator
│   │   ├── lesson_plan_handler.py  # Lesson plan generator
│   │   ├── worksheet_handler.py    # Worksheet generator
│   │   └── quiz_handler.py  # Quiz generator
│   └── utils/               # Utility functions
│       ├── constants.py     # Constants
│       ├── decorators.py    # Function decorators
│       └── outlineFormatter.js # Outline formatting (used by frontend)
└── tests/                   # Test suite
    └── test_app.py          # Application tests
```

## Configuration

The application uses environment variables for configuration, which can be set in a `.env` file:

```
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
DAILY_GENERATION_LIMIT=5
DAILY_DOWNLOAD_LIMIT=5
```

## Development

To set up the development environment:

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file with the required environment variables
5. Run the setup script: `./setup.sh`
6. Start the development server: `./startup.sh dev`

## Testing

Run tests using the test script:

```bash
./test.sh
```

## Deployment

For production deployment:

1. Set environment variables for production
2. Run the setup script: `./setup.sh`
3. Start the production server: `./startup.sh prod`

## Maintenance

### Cleaning Up Unnecessary Files

After consolidating scripts, you can safely remove the following files:

```bash
# Run the cleanup script to remove redundant files
./cleanup.sh
```

Or manually remove:
- `startup.txt` (replaced by `startup.sh`)
- `setup_history.sh` (consolidated into `setup.sh`)
- `setup_history_routes.sh` (consolidated into `setup.sh`)
- `setup_migration.sh` (consolidated into `setup.sh`)
- `setup_recents_list.sh` (consolidated into `setup.sh`)
- `run_migration.sh` (consolidated into `setup.sh`)
- `test_api.sh` (consolidated into `test.sh`)
- `test_rate_limits.sh` (consolidated into `test.sh`)

### Database Migrations

Database migrations are managed through Python scripts in the `src/db/migrations/` directory. The setup script includes functionality to run these migrations.
