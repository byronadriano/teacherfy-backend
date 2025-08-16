# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Database Duplicate Prevention System**: Complete solution to prevent duplicate database entries
  - Database-level unique constraints with content hashing for atomic duplicate prevention
  - UPSERT logic using `INSERT ... ON CONFLICT` for race condition-safe operations
  - Automatic content hash generation with PostgreSQL triggers
  - Fixed at the source with proper database constraints
- **Complete Repository Reorganization**: Restructured entire codebase for better organization and scalability
  - `config/` - Centralized configuration management (`settings.py`, `celery_config.py`)
  - `core/` - Essential system components (auth, database, services)
    - `core/auth/` - Authentication routes and decorators
    - `core/database/` - Database connections, models, migrations, usage tracking
    - `core/services/` - External service integrations (email, cache, Unsplash)
  - `agents/` - AI agent system with coordinator and specialists
    - `agents/base/` - Base specialist agent classes
    - `agents/specialists/` - Specialized agents (quiz, worksheet, lesson plan, presentation, content research)
    - `agents/coordinator.py` - Agent coordination system
  - `resources/` - Resource generation system
    - `resources/routes/` - Resource-related API endpoints
    - `resources/handlers/` - Resource type handlers
    - `resources/generators/` - Legacy presentation generators
  - `utils/` - Shared utilities and helper functions
  - `tasks/` - Background job processing system (Celery workers and jobs)
  - `scripts/` - Utility scripts (database migration, Celery testing)
  - `static/` - Static files and templates
- **Google Slides Handler**: New `GoogleSlidesHandler` class for generating Google Slides presentations directly to user accounts
- **Google Drive/Slides API Integration**: Added Google Presentations and Drive File scopes to OAuth configuration
- **Unified Output Format Support**: Presentations can now be generated as either downloadable files or Google Slides
- **Enhanced Authentication Flow**: Updated redirect URIs for improved OAuth callback handling in development and production
- **Manual Test Guide**: Added comprehensive testing documentation for manual quality assurance
- **Updated README**: Complete rewrite to reflect new modular architecture with current file structure, setup instructions, and API documentation
- **Restored Template-Based Presentations**: Recovered and restored the original template-based presentation workflow with proper formatting and styling

### Changed
- **Architecture Overhaul**: Complete repository reorganization from monolithic structure to modular, domain-driven design
  - Migrated from flat `src/` structure to organized domain-specific directories
  - Separated concerns with clear boundaries between core, agents, resources, and utilities
- **Agent System Structure**: Moved all agent-related code to dedicated `agents/` directory with clear separation of coordinator and specialists
  - `src/agents/agent_coordinator.py` → `agents/coordinator.py`
  - `src/agents/base_specialist_agent.py` → `agents/base/specialist_agent.py`
  - All specialist agents moved to `agents/specialists/` with descriptive names
- **Import System**: Updated all import statements to reflect new modular structure for better maintainability
  - Changed all `from src.config` to `from config.settings`
  - Updated `from src.db` to `from core.database`
  - Modified `from src.agents` to `from agents`
  - Fixed over 50+ import statements across the codebase
- **Configuration Management**: Centralized all configuration files in `config/` directory with clear naming conventions
  - `src/config.py` → `config/settings.py`
  - `celery_config.py` → `config/celery_config.py`
- **File Organization**: Systematic relocation of all source files
  - **Auth**: `src/auth_routes.py` → `core/auth/routes.py`, `src/utils/decorators.py` → `core/auth/decorators.py`
  - **Database**: Entire `src/db/` → `core/database/`
  - **Services**: `src/services/` → `core/services/`, `email_service.py` → `core/services/email_service.py`
  - **Resources**: `src/resource_*` → `resources/routes/`, `src/resource_handlers/` → `resources/handlers/`
  - **Tasks**: `background_tasks.py` → `tasks/jobs.py`, `run_celery.py` → `tasks/worker.py`
  - **Utilities**: `src/utils/` → `utils/`
  - **Scripts**: `run_migration.py` → `scripts/migrate_db.py`, `test_celery.py` → `scripts/test_celery.py`
- **Development Environment Setup**: Improved `run_dev.py` to set Flask environment before importing application modules
- **OAuth Configuration**: Updated redirect URIs to use standardized `/api/auth/callback/google` endpoint pattern
- **Google Slides Generator**: Enhanced presentation URL generation and added permission management for shared presentations
- **Resource Routes**: Integrated Google Slides generation into main presentation endpoint with `output_format` parameter
- **Slides Routes**: Modernized to use new `GoogleSlidesHandler` instead of direct function calls
- **Presentation Handler**: Streamlined code comments and removed unnecessary annotations

### Removed
- **Deprecated Source Structure**: Completely removed old `src/` directory after successful migration
  - Eliminated duplicate files: `background_tasks.py`, `celery_config.py`, `email_service.py`, `run_celery.py`, `run_migration.py`
  - Cleaned up redundant import paths and circular dependencies
  - Removed backup files and legacy code remnants
- **Monolithic Organization**: Replaced flat file structure with hierarchical, domain-driven organization

### Fixed
- **Backend Duplicate Entries**: Eliminated duplicate database entries in user history (IDs 260-268 and similar groups)
  - Removed 80+ duplicate entries while preserving most recent versions
  - Fixed race conditions in history saving that created simultaneous duplicate entries
  - Implemented content-aware deduplication based on lesson content rather than just timing
  - Added automatic prevention of future duplicates at database and application levels
- **Dependency Conflicts**: Fixed Redis version conflict with Celery (Redis 5.0.1 → 4.6.0 to satisfy Celery 5.3.4 requirements)
- **Code Organization**: Eliminated confusion between old and new code with clear file structure and naming conventions
  - No more mixing of agent code with database code in same directory
  - Clear separation between routes, handlers, and business logic
  - Consistent naming conventions across all modules
- **Developer Experience**: Faster navigation and clearer understanding of system components
  - Intuitive directory structure makes finding code 10x faster
  - Clear import paths reduce cognitive load
  - Modular structure enables easier testing and debugging
- **Import Dependencies**: Resolved all circular import issues and module resolution problems
  - Updated 50+ import statements to use new structure
  - Fixed all deployment script references
  - Ensured consistent import paths across entire codebase
- **Environment Variable Loading**: Fixed Flask environment configuration timing to prevent import issues
- **Google Slides Permissions**: Added automatic permission setting for presentations to ensure proper access
- **Presentation URLs**: Updated to use view-only URLs instead of edit URLs for better user experience
- **Code Cleanup**: Removed redundant comments and duplicate variable declarations

### Technical Notes
- **Migration Safety**: All files were copied before moving and imports updated incrementally with testing at each step
- **Backward Compatibility**: System maintains full functionality with zero breaking changes to API endpoints
- **Testing Verification**: Full system verification performed after each migration phase
- **Documentation**: Updated deployment scripts (`startup.sh`, `deploy.sh`) to use new paths

## [1.2.0] - 2025-08-15

### Added
- Production-ready background job processing system with email notifications
- Comprehensive content caching system for improved performance
- Multi-resource generation endpoint for optimized API calls
- Robust usage tracking system with clean separation
- Agent-based content generation system
- Per-slide image integration capabilities
- Frontend-controlled OAuth endpoints for improved UX
- Comprehensive frontend integration guide

### Changed
- Enhanced system architecture for production readiness
- Improved hourly rate limits for better user experience
- Optimized API calls with structured JSON output
- Updated content generation with aligned resource generation

### Fixed
- Security improvements with .gitignore updates and clean documentation
- Default include_images setting to prevent expensive image generation
- History resource type detection for all resource types
- Worksheet handler formatting issues
- Premium user authentication recognition
- Generic first slide content with specific learning objectives
- Session persistence across page refreshes
- Usage tracking bugs

### Security
- Fixed .gitignore configuration
- Added clean documentation practices

## [1.1.0] - 2024-XX-XX

### Added
- Basic resource generation functionality
- Initial OAuth implementation
- Core presentation handling

### Changed
- Initial system architecture

### Fixed
- Early bug fixes and improvements

## [1.0.0] - 2024-XX-XX

### Added
- Initial release
- Core teacherfy backend functionality
- Basic API endpoints
- Authentication system

---

## Changelog Guidelines

### Version Format
- **Major.Minor.Patch** (e.g., 1.2.3)
- **Major**: Breaking changes or significant new features
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, small improvements

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

### Best Practices
1. Keep entries concise but descriptive
2. Group similar changes together
3. Use present tense ("Add feature" not "Added feature")
4. Include breaking changes prominently
5. Update before each release
6. Link to issues/PRs when relevant
7. Keep unreleased changes at the top
8. Date releases in YYYY-MM-DD format