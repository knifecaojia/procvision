# Project Context

## Purpose
05ui-poc is an Industrial Vision System (SMART-VISION) designed for manufacturing and industrial environments. The application provides secure user authentication, camera management, AI model visualization, process monitoring, and records management for industrial quality control and inspection processes.

## Tech Stack
- **Python 3.8+**: Core application language with type hints
- **PySide6 6.8.0.2**: Qt6 Python bindings for cross-platform desktop GUI
- **bcrypt 4.2.0**: Password hashing for secure authentication
- **SQLite**: Embedded database for user authentication and session management
- **Optional Testing**: pytest, pytest-qt for unit testing
- **Optional Linting**: ruff for code quality

### Configuration Files
- **Requirements**: `requirements.txt` with PySide6 and bcrypt pinned to specific versions
- **Git Config**: `.gitignore` excludes Python cache, virtual environments, logs, databases, and temp files
- **Config Directory**: `config/app_config.json` stores runtime settings (auto-generated)
- **Data Directory**: `data/` stores SQLite databases and backups

### Development Commands
- **Run Application**: `python run_app.py`
- **Run Tests**: `cd src; pytest`
- **Lint Code**: `ruff check .`
- **Create Default User**: `python scripts/create_default_user.py`
- **Quick Test**: `python test_login.py`

## Project Conventions

### Code Style
- **Python 3.8+**: Type hints encouraged, follow standard PEP conventions
- **Docstrings**: Required for all classes, functions, and modules using triple quotes
- **Imports**: Grouped as: standard library → third-party → local imports
- **Error Handling**: Comprehensive try-except blocks with appropriate logging
- **Logging**: Use Python's logging module with appropriate levels (DEBUG, INFO, WARNING, ERROR)
- **Line Length**: 120 characters maximum (configurable between 79-120)
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants

### Architecture Patterns
- **Modular Structure**: Clear separation between core, ui, auth, and utils modules
- **Configuration Management**: Centralized config via dataclasses in `src/core/config.py`
- **Session Management**: Persistent user sessions with timeout validation
- **Window Management**: Login → Main application flow with proper cleanup
- **Error Handling**: Comprehensive exception handling with fallback behaviors
- **Security**: bcrypt password hashing, input validation, reserved username protection

### Testing Strategy
- **Unit Tests**: Located in `tests/` directory, typically focused on auth services
- **Manual Testing**: Quick test scripts available for validation (test_login.py, test_model_card.py)
- **Test Commands**: Run tests from `src` directory: `cd src; pytest`
- **No Auto-Write**: Tests are not automatically written during development

### Git Workflow
- **Feature Branches**: Individual feature branches (e.g., 001-create-login-flow)
- **Commit Messages**: Clear, descriptive messages documenting changes
- **No Auto-Commits**: Commits only when explicitly requested by user
- **Project Documentation**: OpenSpec methodology for structured feature planning

### UI Design System
- **Industrial Theme**: Deep graphite (#1A1D23), steel grey (#1F232B), arctic white (#F2F4F8)
- **Accent Colors**: Hover orange (#FF8C32), success green (#3CC37A), error red (#E85454)
- **Custom Fonts**: Arial/Noto Sans fallback system
- **Frameless Windows**: Custom title bars with window controls
- **Responsive Design**: Grid layouts with minimum 150px spacing for industrial touchscreens

## Domain Context

### Industrial Vision System Features
- **Multi-User Authentication**: Role-based access with bcrypt password security
- **Camera Management**: Real-time camera feed integration and controls
- **AI Model Integration**: Model configuration, status monitoring, and visualization
- **Process Monitoring**: Real-time process control and status updates
- **Records Management**: Data logging and historical record review
- **System Configuration**: Application settings and preferences

### User Experience Flow
1. **Login**: Username/password authentication with session persistence
2. **Main Dashboard**: Process page as default view with real-time status
3. **Navigation**: Sidebar navigation between 5 main pages (Process, Model, Records, Camera, System)
4. **Session Management**: 8-hour session timeout with automatic logout on inactivity

### Technical Considerations
- **Cross-Platform**: Windows/Linux compatibility via PySide6
- **Embedded Database**: SQLite for standalone deployment without external DB
- **Hardware Integration**: Designed for industrial PCs with touchscreen support
- **Error Recovery**: Graceful degradation and fallback behaviors for critical errors
- **Logging**: Comprehensive logging for debugging and audit trails

## Important Constraints

### Security Requirements
- **Password Security**: Minimum 8 characters, bcrypt hashing with cost factor 12
- **Input Validation**: Validation for all user inputs to prevent injection attacks
- **Session Protection**: Token-based sessions with timeout validation
- **Username Restrictions**: Reserved usernames ('administrator', 'root', 'system') blocked

### Technical Constraints
- **Python Version**: Minimum Python 3.8 required for type hints
- **Dependency Versions**: PySide6 6.8.0.2 is pinned for Qt6 compatibility
- **Directory Structure**: Strict modularity with `src/`, `tests/`, `config/`, `data/`, `logs/`
- **Database Location**: SQLite databases must be in `data/` directory
- **Configuration Files**: JSON-based config with fallback to environment variables

### Performance Considerations
- **Startup Time**: Should initialize within 3-5 seconds on industrial hardware
- **Memory Usage**: Minimal footprint for embedded industrial PCs
- **Responsiveness**: UI animations limited to 200ms duration
- **File Watching**: Dynamic stylesheet reloading in development mode only

## External Dependencies

### Required Dependencies
- **PySide6**: Qt6 Python bindings for GUI framework
- **bcrypt**: Password hashing library
- **Python Standard Library**: sqlite3, json, logging, datetime, pathlib, dataclasses

### Optional Development Tools
- **pytest**: Unit testing framework
- **pytest-qt**: Qt application testing
- **ruff**: Python linting and code quality
- **black**: Code formatting (currently commented out in requirements)

### System Integration
- **Qt Framework**: Native look and feel on Windows/Linux
- **Font System**: Custom font loading from project resources
- **File System**: SQLite database in `data/auth.db` with automatic backup

### Default Credentials
- **Admin User**: Username: `admin`, Password: `admin123` (created via `scripts/create_default_user.py`)
- **Session Timeout**: 8 hours with 30-minute cleanup intervals
- **Language Support**: Chinese (中) and English with configurable defaults
