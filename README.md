# Teacherfy Backend

A robust, scalable backend API for generating educational resources using AI, built with Flask, Celery, and Docker.

## Overview

Teacherfy is an AI-powered platform for creating educational content, including presentations, lesson plans, worksheets, and quizzes. This repository contains the backend service built with Flask, PostgreSQL, and a modular agent-based architecture with containerized deployment.

## ✨ Features

- **Multi-Resource Generation**: Create presentations, lesson plans, worksheets, and quizzes
- **AI Agent System**: Specialized agents for different content types with coordinator
- **Google Slides Integration**: Direct creation and sharing of Google Slides presentations
- **Background Job Processing**: Celery-based background tasks with email notifications
- **Usage Tracking**: Comprehensive usage limits and subscription management
- **OAuth Authentication**: Google OAuth integration for secure user authentication

## 🏗️ Architecture

The backend uses a modular, domain-driven architecture with clear separation of concerns:

```
teacherfy-backend/
├── 📋 app.py                    # Main Flask application  
├── 🚀 deploy.sh                 # Azure deployment script
├── 🛠️ startup.sh                # Legacy startup script
├── 📦 requirements.txt          # Python dependencies
├── 
├── 📁 config/                   # Configuration management
│   ├── settings.py              # Main configuration settings
│   └── celery_config.py         # Celery background job configuration
├── 
├── 📁 core/                     # Core system components
│   ├── auth/                    # Authentication system
│   │   ├── routes.py            # OAuth routes and session management
│   │   └── decorators.py        # Authentication decorators
│   ├── database/                # Database layer
│   │   ├── database.py          # Database connections and utilities
│   │   ├── usage.py             # Usage tracking and limits
│   │   ├── usage_v2.py          # Enhanced usage tracking
│   │   ├── migrations/          # Database migration scripts
│   │   └── schema.sql           # Database schema
│   └── services/                # External service integrations
│       ├── content_cache.py     # Content caching service
│       ├── email_service.py     # Email notification service
│       └── unsplash_service.py  # Image service integration
├── 
├── 📁 agents/                   # AI Agent system
│   ├── coordinator.py           # Agent coordination and orchestration
│   ├── base/                    # Base agent classes
│   │   └── specialist_agent.py  # Base specialist agent
│   └── specialists/             # Specialized content agents
│       ├── content_research.py  # Content research agent
│       ├── lesson_plan.py       # Lesson plan generation agent
│       ├── quiz_generator.py    # Quiz generation agent
│       ├── worksheet_generator.py # Worksheet generation agent
│       └── presentation.py     # Presentation content agent
├── 
├── 📁 resources/                # Resource generation system
│   ├── routes/                  # Resource API endpoints
│   │   ├── outlines.py          # Content outline generation
│   │   ├── resources.py         # Multi-resource generation
│   │   ├── presentations.py     # Google Slides integration
│   │   └── history.py           # Generation history
│   ├── handlers/                # Resource type handlers
│   │   ├── base_handler.py      # Base resource handler
│   │   ├── presentation_handler.py # Presentation generation
│   │   ├── lesson_plan_handler.py  # Lesson plan handling
│   │   ├── quiz_handler.py      # Quiz generation
│   │   ├── worksheet_handler.py # Worksheet creation
│   │   └── google_slides_handler.py # Google Slides API
│   ├── generators/              # Legacy generators
│   │   ├── google_slides.py     # Google Slides generator
│   │   └── presentation.py      # Presentation generator
│   └── types.py                 # Resource type definitions
├── 
├── 📁 tasks/                    # Background job processing
│   ├── jobs.py                  # Celery job definitions
│   └── worker.py                # Celery worker configuration
├── 
├── 📁 utils/                    # Shared utilities
│   ├── constants.py             # Application constants
│   ├── decorators.py            # Utility decorators
│   └── subject_guidance.py      # Subject-specific guidance
├── 
├── 📁 scripts/                  # Utility scripts
│   ├── migrate_db.py            # Database migration utility
│   └── test_celery.py           # Celery testing utility
├── 
├── 📁 static/                   # Static files
│   └── templates/               # PowerPoint templates
├── 
└── 📁 tests/                    # Test suite
    ├── unit/                    # Unit tests
    ├── integration/             # Integration tests
    └── test_*.py                # Test files
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop
- Git
- Azure CLI (for production deployment)

### Local Development

1. **Clone and setup**:
```bash
git clone <repository-url>
cd teacherfy-backend
cp .env.example .env
# Edit .env with your configuration
```

2. **Start development environment**:
```bash
./scripts/dev.sh
```

3. **Access services**:
   - **API**: http://localhost:5000
   - **Flower Dashboard**: http://localhost:5555
   - **Health Check**: http://localhost:5000/health

### Manual Docker Commands

```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Shell access
docker-compose exec web bash
docker-compose exec worker bash
```

### Production Deployment

Deploy to Azure with automated scripts:

```bash
# Deploy infrastructure and application
./scripts/deploy.sh latest

# Or deploy manually to existing infrastructure
docker build -f Dockerfile.web -t teacherfy-web .
docker build -f Dockerfile.worker -t teacherfy-worker .
# Push to Azure Container Registry and deploy
```

### Alternative: Traditional Python Development

If you need to develop without Docker (not recommended):

1. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start development server**:
   ```bash
   ./startup.sh dev
   ```

⚠️ **Note**: Background jobs won't work without Docker/Redis. Use Docker for full functionality.

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Flask Configuration
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key-here
PORT=5000

# AI API
DEEPSEEK_API_KEY=your-deepseek-api-key

# Database
POSTGRES_DB=teacherfy_db
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Google OAuth & API
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Redis (for background jobs)
REDIS_URL=redis://localhost:6379/0

# Usage Limits
MONTHLY_GENERATION_LIMIT=15
MONTHLY_DOWNLOAD_LIMIT=15

# External Services
UNSPLASH_ACCESS_KEY=your-unsplash-key
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test Celery and Redis setup
python scripts/test_celery.py

# Run application tests
pytest

# Test specific components
python -c "from app import create_app; app = create_app(); print('✅ App creation successful')"
```

## 🚀 Deployment

### Azure App Service

The repository includes Azure-specific deployment configuration:

```bash
# Deploy to Azure
./deploy.sh

# Or use startup script for production
./startup.sh prod
```

### Manual Production Setup

1. Set production environment variables
2. Configure PostgreSQL and Redis
3. Run database migrations
4. Start with Gunicorn:
   ```bash
   gunicorn --bind=0.0.0.0:5000 --workers=4 app:app
   ```

## 🏗️ Development

### Adding New Resource Types

1. Create a new specialist agent in `agents/specialists/`
2. Add a new handler in `resources/handlers/`
3. Update the coordinator in `agents/coordinator.py`
4. Add routes in `resources/routes/`

### Database Migrations

1. Create migration scripts in `core/database/migrations/`
2. Run migrations: `python scripts/migrate_db.py`

### Background Jobs

1. Define jobs in `tasks/jobs.py`
2. Start Celery worker: `celery -A tasks.worker:celery_app worker`
3. Monitor with Celery Flower if needed

## 🔧 API Endpoints

### Authentication
- `POST /auth/login/{provider}` - Initiate OAuth login
- `GET /api/auth/callback/{provider}` - OAuth callback
- `GET /auth/check` - Check authentication status

### Content Generation
- `POST /generate/outline` - Generate content outline
- `POST /generate/resources` - Generate multiple resources
- `POST /generate/presentation` - Generate presentation (file or Google Slides)

### Background Jobs (New!)
- `POST /generate/background` - Start background resource generation
- `GET /generate/status/{job_id}` - Check job status and progress
- `POST /generate/cancel/{job_id}` - Cancel running job

### History & Management
- `GET /history` - Get generation history
- `GET /usage` - Check usage limits
- `GET /health` - Service health check

### Monitoring
- **Flower Dashboard**: http://localhost:5555 (development)
- Real-time Celery worker monitoring and task tracking

## 🤝 Contributing

1. Follow the modular architecture patterns
2. Add tests for new features
3. Update documentation
4. Ensure all imports use the new structure
5. Test thoroughly before committing

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Check the troubleshooting section in `/docs`
- Review test output: `python scripts/test_celery.py`
- Verify configuration: `python -c "from config.settings import config; print('Config loaded successfully')"`

---

*Built with ❤️ using Flask, PostgreSQL, Celery, and AI agents*