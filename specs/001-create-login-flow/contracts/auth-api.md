# Authentication API Contracts

**Date**: 2025-11-06
**Feature**: Create Login Flow with Main Page Navigation

## Authentication Service Interface

This document defines the internal API contracts for the authentication system in the industrial vision application.

## Core Authentication Service

### IAuthService Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from datetime import datetime

class IAuthService(ABC):
    """Authentication service interface for the industrial vision application"""

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate user credentials

        Args:
            username: User's username
            password: User's password (plaintext)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        pass

    @abstractmethod
    async def create_session(self, user_id: int) -> str:
        """
        Create new authentication session

        Args:
            user_id: ID of authenticated user

        Returns:
            Session token string
        """
        pass

    @abstractmethod
    async def validate_session(self, session_token: str) -> Optional[User]:
        """
        Validate session token and return user

        Args:
            session_token: Session token to validate

        Returns:
            User object if valid, None otherwise
        """
        pass

    @abstractmethod
    async def logout(self, session_token: str) -> bool:
        """
        Terminate user session

        Args:
            session_token: Session token to terminate

        Returns:
            True if session was terminated, False if not found
        """
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions

        Returns:
            Number of sessions cleaned up
        """
        pass
```

## User Storage Interface

### IUserStorage Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, List

class IUserStorage(ABC):
    """User data storage interface"""

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieve user by username"""
        pass

    @abstractmethod
    async def create_user(self, username: str, password_hash: str, **kwargs) -> User:
        """Create new user account"""
        pass

    @abstractmethod
    async def update_last_login(self, user_id: int, login_time: datetime) -> bool:
        """Update user's last login timestamp"""
        pass

    @abstractmethod
    async def update_user_preferences(self, user_id: int, preferences: dict) -> bool:
        """Update user preferences (language, remember_username, etc.)"""
        pass
```

## Session Storage Interface

### ISessionStorage Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, List

class ISessionStorage(ABC):
    """Session data storage interface"""

    @abstractmethod
    async def create_session(self, session_id: str, user_id: int, expires_at: datetime) -> bool:
        """Create new session record"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[AuthSession]:
        """Retrieve session by ID"""
        pass

    @abstractmethod
    async def update_session_expiry(self, session_id: str, new_expiry: datetime) -> bool:
        """Update session expiration time"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session record"""
        pass

    @abstractmethod
    async def get_user_sessions(self, user_id: int) -> List[AuthSession]:
        """Get all active sessions for a user"""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions"""
        pass
```

## UI Event Contracts

### Login Window Events

```python
from typing import Protocol

class LoginWindowEvents(Protocol):
    """Event contracts for login window UI interactions"""

    def on_login_attempt(self, username: str, password: str, remember_me: bool, language: str) -> None:
        """Handle login form submission"""
        ...

    def on_language_changed(self, language: str) -> None:
        """Handle language selection change"""
        ...

    def on_remember_username_toggled(self, remember: bool) -> None:
        """Handle remember username checkbox toggle"""
        ...

    def on_window_close(self) -> bool:
        """Handle window close event, return True to allow close"""
        ...
```

### Main Window Events

```python
class MainWindowEvents(Protocol):
    """Event contracts for main window UI interactions"""

    def on_logout_request(self) -> None:
        """Handle user logout request"""
        ...

    def on_session_expiry(self) -> None:
        """Handle automatic session expiry"""
        ...

    def on_camera_status_update(self, camera_id: str, status: bool) -> None:
        """Handle camera connection status updates"""
        ...
```

## Application State Contracts

### Authentication State Manager

```python
class IAuthStateManager(Protocol):
    """Authentication state management interface"""

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        ...

    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user"""
        ...

    def get_session_token(self) -> Optional[str]:
        """Get current session token"""
        ...

    def set_authenticated_state(self, user: User, session_token: str) -> None:
        """Set authenticated state after successful login"""
        ...

    def clear_authentication_state(self) -> None:
        """Clear authentication state after logout"""
        ...

    def check_session_validity(self) -> bool:
        """Check if current session is still valid"""
        ...
```

## Error Handling Contracts

### Authentication Errors

```python
from enum import Enum

class AuthErrorType(Enum):
    """Authentication error types"""
    INVALID_CREDENTIALS = "invalid_credentials"
    USER_NOT_FOUND = "user_not_found"
    USER_INACTIVE = "user_inactive"
    SESSION_EXPIRED = "session_expired"
    SESSION_INVALID = "session_invalid"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"

class AuthError(Exception):
    """Custom authentication error"""

    def __init__(self, error_type: AuthErrorType, message: str, details: dict = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

## Configuration Contracts

### Authentication Configuration

```python
@dataclass
class AuthConfig:
    """Authentication system configuration"""

    # Security settings
    bcrypt_cost_factor: int = 12
    session_timeout_hours: int = 8
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Database settings
    database_path: str = "data/auth.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24

    # UI settings
    default_language: str = "中"
    supported_languages: List[str] = field(default_factory=lambda: ["中", "English"])
    remember_username_default: bool = False

    # Session settings
    max_sessions_per_user: int = 3
    session_cleanup_interval_minutes: int = 30
```

## Integration Points

### Database Integration

```python
class IDatabaseConnection(Protocol):
    """Database connection interface"""

    async def execute_query(self, query: str, params: tuple = ()) -> List[dict]:
        """Execute SQL query and return results"""
        ...

    async def execute_command(self, command: str, params: tuple = ()) -> bool:
        """Execute SQL command (INSERT, UPDATE, DELETE)"""
        ...

    async def begin_transaction(self) -> None:
        """Begin database transaction"""
        ...

    async def commit_transaction(self) -> None:
        """Commit database transaction"""
        ...

    async def rollback_transaction(self) -> None:
        """Rollback database transaction"""
        ...
```

These contracts define the interfaces and data structures needed for implementing the authentication system while maintaining clean separation of concerns and testability in the industrial vision application.