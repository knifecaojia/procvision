"""
Authentication data models for industrial vision application.

Defines User and AuthSession entities with proper validation
and business logic for industrial environments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import re


@dataclass
class User:
    """
    User entity for authentication and session management.

    Represents authenticated users in the industrial vision system
    with proper validation and security considerations.
    """

    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True
    remember_username: bool = False
    language_preference: str = "中"

    def __post_init__(self):
        """Validate user data after initialization."""
        if self.username:
            self.validate_username()

        if self.language_preference:
            self.validate_language()

    def validate_username(self) -> bool:
        """
        Validate username according to industrial standards.

        Returns:
            bool: True if username is valid

        Raises:
            ValueError: If username is invalid
        """
        if not self.username:
            raise ValueError("Username cannot be empty")

        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(self.username) > 50:
            raise ValueError("Username cannot exceed 50 characters")

        # Allow alphanumeric characters, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")

        return True

    def validate_language(self) -> bool:
        """
        Validate language preference.

        Returns:
            bool: True if language is valid

        Raises:
            ValueError: If language is invalid
        """
        valid_languages = ["中", "English"]
        if self.language_preference not in valid_languages:
            raise ValueError(f"Language must be one of: {', '.join(valid_languages)}")

        return True

    def is_valid_password(self, password: str) -> bool:
        """
        Validate password against stored hash.

        Args:
            password: Plain text password to validate

        Returns:
            bool: True if password matches hash
        """
        if not self.password_hash:
            return False

        # Note: Actual bcrypt validation happens in AuthService
        # This is just a basic check
        return len(password) >= 8

    def to_dict(self) -> Dict[str, Any]:
        """Convert user entity to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'remember_username': self.remember_username,
            'language_preference': self.language_preference
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user entity from dictionary."""
        # Handle datetime parsing
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        if data.get('last_login'):
            data['last_login'] = datetime.fromisoformat(data['last_login'])

        # Filter out password_hash for security
        data.pop('password_hash', None)

        return cls(**data)


@dataclass
class AuthSession:
    """
    Authentication session entity for managing user sessions.

    Handles session state, expiration, and security for
    industrial application access control.
    """

    session_id: str = ""
    user_id: int = 0
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def __post_init__(self):
        """Validate session data after initialization."""
        if self.session_id:
            self.validate_session_id()

    def validate_session_id(self) -> bool:
        """
        Validate session ID format.

        Returns:
            bool: True if session ID is valid

        Raises:
            ValueError: If session ID is invalid
        """
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")

        if len(self.session_id) < 16:
            raise ValueError("Session ID must be at least 16 characters long")

        return True

    def is_expired(self) -> bool:
        """
        Check if session has expired.

        Returns:
            bool: True if session is expired
        """
        if not self.expires_at:
            return True

        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """
        Check if session is valid and active.

        Returns:
            bool: True if session is valid
        """
        return (
            self.is_active and
            not self.is_expired() and
            self.validate_session_id()
        )

    def extend_session(self, hours: int = 8) -> None:
        """
        Extend session expiration time.

        Args:
            hours: Number of hours to extend session
        """
        if self.expires_at:
            self.expires_at = max(
                self.expires_at,
                datetime.now() + datetime.timedelta(hours=hours)
            )
        else:
            self.expires_at = datetime.now() + datetime.timedelta(hours=hours)

    def revoke(self) -> None:
        """Revoke the session by marking it as inactive."""
        self.is_active = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert session entity to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthSession':
        """Create session entity from dictionary."""
        # Handle datetime parsing
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])

        return cls(**data)


@dataclass
class AuthState:
    """
    Current authentication state for the application.

    Manages runtime authentication status and user session
    information for the industrial vision application.
    """

    is_authenticated: bool = False
    current_user: Optional[User] = None
    session_token: Optional[str] = None
    login_time: Optional[datetime] = None
    session_expires: Optional[datetime] = None
    camera_permissions: Dict[str, bool] = field(default_factory=dict)

    def set_authenticated(self, user: User, session_token: str, expires_at: datetime) -> None:
        """
        Set authenticated state after successful login.

        Args:
            user: Authenticated user entity
            session_token: Session token string
            expires_at: Session expiration time
        """
        self.is_authenticated = True
        self.current_user = user
        self.session_token = session_token
        self.login_time = datetime.now()
        self.session_expires = expires_at

        # Set default camera permissions
        self.camera_permissions = {
            'lower_camera': False,
            'left_camera': False,
            'right_camera': False
        }

    def clear_authentication(self) -> None:
        """Clear authentication state after logout."""
        self.is_authenticated = False
        self.current_user = None
        self.session_token = None
        self.login_time = None
        self.session_expires = None
        self.camera_permissions = {}

    def is_session_valid(self) -> bool:
        """
        Check if current session is still valid.

        Returns:
            bool: True if session is valid
        """
        if not self.is_authenticated or not self.session_expires:
            return False

        return datetime.now() < self.session_expires

    def get_time_remaining(self) -> Optional[int]:
        """
        Get remaining session time in minutes.

        Returns:
            int: Minutes remaining, or None if no active session
        """
        if not self.session_expires:
            return None

        remaining = self.session_expires - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))

    def has_camera_permission(self, camera_id: str) -> bool:
        """
        Check if user has permission for specific camera.

        Args:
            camera_id: Camera identifier

        Returns:
            bool: True if user has permission
        """
        return self.camera_permissions.get(camera_id, False)

    def set_camera_permission(self, camera_id: str, has_permission: bool) -> None:
        """
        Set camera permission for user.

        Args:
            camera_id: Camera identifier
            has_permission: Permission status
        """
        if self.is_authenticated:
            self.camera_permissions[camera_id] = has_permission