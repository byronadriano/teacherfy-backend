# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Google Slides Handler**: New `GoogleSlidesHandler` class for generating Google Slides presentations directly to user accounts
- **Google Drive/Slides API Integration**: Added Google Presentations and Drive File scopes to OAuth configuration
- **Unified Output Format Support**: Presentations can now be generated as either downloadable files or Google Slides
- **Enhanced Authentication Flow**: Updated redirect URIs for improved OAuth callback handling in development and production
- **Manual Test Guide**: Added comprehensive testing documentation for manual quality assurance

### Changed
- **Development Environment Setup**: Improved `run_dev.py` to set Flask environment before importing application modules
- **OAuth Configuration**: Updated redirect URIs to use standardized `/api/auth/callback/google` endpoint pattern
- **Google Slides Generator**: Enhanced presentation URL generation and added permission management for shared presentations
- **Resource Routes**: Integrated Google Slides generation into main presentation endpoint with `output_format` parameter
- **Slides Routes**: Modernized to use new `GoogleSlidesHandler` instead of direct function calls
- **Presentation Handler**: Streamlined code comments and removed unnecessary annotations

### Fixed
- **Environment Variable Loading**: Fixed Flask environment configuration timing to prevent import issues
- **Google Slides Permissions**: Added automatic permission setting for presentations to ensure proper access
- **Presentation URLs**: Updated to use view-only URLs instead of edit URLs for better user experience
- **Code Cleanup**: Removed redundant comments and duplicate variable declarations

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