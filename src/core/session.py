"""
Session management for industrial vision application.

Provides high-level session state management and authentication
status tracking throughout the application lifecycle.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

try:
    from ..auth.models import User, AuthState
except ImportError:
    from src.auth.models import User, AuthState

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user authentication session state for the industrial vision application.

    Handles session lifecycle, authentication state, and provides
    a simple interface for UI components to check user status.
    """

    def __init__(self, auth_service=None):
        """Initialize session manager with authentication service."""
        self.auth_state = AuthState()
        self._session_timeout_hours = 8
        self.auth_service = auth_service

    def set_authenticated_session(self, user_info, session_token: str, expires_at: Optional[datetime] = None) -> None:
        """
        Set authenticated session data after successful login.

        Args:
            user_info: Authenticated user entity or username string
            session_token: Session token string
            expires_at: Session expiration time
        """
        if isinstance(user_info, User):
            user = user_info
        else:
            user = User(username=str(user_info))

        if not user.language_preference:
            user.language_preference = "中"

        # Set session expiration
        if expires_at is None:
            expires_at = datetime.now() + timedelta(hours=self._session_timeout_hours)

        # Update authentication state
        self.auth_state.set_authenticated(user, session_token, expires_at)

        logger.info(f"Session set for user: {user.username}")

    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated and session is valid.

        Returns:
            bool: True if user is authenticated and session is valid
        """
        return self.auth_state.is_authenticated and self.auth_state.is_session_valid()

    def get_username(self) -> Optional[str]:
        """
        Get current authenticated username.

        Returns:
            str: Current username or None if not authenticated
        """
        return self.auth_state.current_user.username if self.auth_state.current_user else None

    def get_session_token(self) -> Optional[str]:
        """
        Get current session token.

        Returns:
            str: Session token or None if not authenticated
        """
        return self.auth_state.session_token

    def get_language_preference(self) -> str:
        """
        Get user's language preference.

        Returns:
            str: Language preference ("中" or "English")
        """
        if self.auth_state.current_user:
            return self.auth_state.current_user.language_preference
        return "中"  # Default language

    def get_session_remaining_time(self) -> Optional[int]:
        """
        Get remaining session time in minutes.

        Returns:
            int: Minutes remaining in session, or None if no active session
        """
        return self.auth_state.get_time_remaining()

    def extend_session(self, hours: int = 8) -> None:
        """
        Extend current session expiration time.

        Args:
            hours: Number of hours to extend session
        """
        if self.auth_state.session_expires:
            self.auth_state.session_expires = datetime.now() + timedelta(hours=hours)
            logger.info("Session extended")

    def check_session_validity(self) -> bool:
        """Return True if current session is still valid."""
        return self.auth_state.is_session_valid()

    def login(self, username: str, password: str, language: str = None, ip_address: str = None, user_agent: str = None):
        """
        Authenticate user and create session.

        Args:
            username: Username to authenticate
            password: Password to authenticate
            language: User's language preference
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            if not self.auth_service:
                return False, "Authentication service not available"

            # Attempt authentication
            success, error_message = self.auth_service.authenticate_user(username, password)
            if not success:
                return False, error_message

            # Retrieve full user profile
            user_data = self.auth_service.get_user_by_username(username)
            if not user_data:
                return False, "Failed to load user profile"

            user = User.from_dict(user_data)

            # Create new session token
            session_token = self.auth_service.create_session(
                user_id=user_data.get("id"),
                ip_address=ip_address,
                user_agent=user_agent
            )

            if not session_token:
                return False, "Failed to create session"

            # Retrieve session info to determine expiration
            session_data = self.auth_service.session_storage.get_session(session_token)
            expires_at = None
            if session_data and session_data.get("expires_at"):
                try:
                    expires_at = datetime.fromisoformat(str(session_data["expires_at"]))
                except ValueError:
                    expires_at = datetime.now() + timedelta(hours=self._session_timeout_hours)
            else:
                expires_at = datetime.now() + timedelta(hours=self._session_timeout_hours)

            # Store session state locally
            self.set_authenticated_session(user, session_token, expires_at)

            # Persist user preferences when provided
            if language:
                self.update_user_preferences(language=language)
                try:
                    self.auth_service.update_user_preferences(
                        username,
                        {'language_preference': language}
                    )
                except Exception as pref_error:
                    logger.warning(f"Failed to persist language preference: {pref_error}")

            logger.info(f"User {username} logged in successfully")
            return True, None

        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def logout(self) -> None:
        """Clear authentication session and logout user."""
        username = self.get_username()
        self.auth_state.clear_authentication()

        if username:
            logger.info(f"User logged out: {username}")

    def update_user_preferences(self, language: Optional[str] = None, remember_username: Optional[bool] = None) -> None:
        """
        Update user preferences in current session.

        Args:
            language: Language preference
            remember_username: Remember username preference
        """
        if self.auth_state.current_user:
            if language is not None:
                self.auth_state.current_user.language_preference = language
                logger.info(f"Language preference updated to: {language}")

            if remember_username is not None:
                self.auth_state.current_user.remember_username = remember_username
                logger.info(f"Remember username preference updated to: {remember_username}")

    def set_camera_permissions(self, camera_permissions: dict) -> None:
        """
        Set camera permissions for current user.

        Args:
            camera_permissions: Dictionary of camera permissions
        """
        if self.auth_state.current_user:
            self.auth_state.camera_permissions = camera_permissions
            logger.info("Camera permissions updated")

    def has_camera_permission(self, camera_id: str) -> bool:
        """
        Check if user has permission for specific camera.

        Args:
            camera_id: Camera identifier

        Returns:
            bool: True if user has permission
        """
        return self.auth_state.has_camera_permission(camera_id)

    def get_login_time(self) -> Optional[datetime]:
        """
        Get when user logged in.

        Returns:
            datetime: Login time or None if not authenticated
        """
        return self.auth_state.login_time

    def get_session_duration(self) -> Optional[str]:
        """
        Get formatted session duration string.

        Returns:
            str: Formatted duration (e.g., "2h 30m") or None if not authenticated
        """
        if not self.auth_state.login_time:
            return None

        duration = datetime.now() - self.auth_state.login_time
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def is_session_expiring_soon(self, minutes_threshold: int = 30) -> bool:
        """
        Check if session is expiring soon.

        Args:
            minutes_threshold: Minutes threshold for "soon"

        Returns:
            bool: True if session expires within threshold
        """
        remaining = self.get_session_remaining_time()
        return remaining is not None and remaining <= minutes_threshold

    def get_session_info(self) -> dict:
        """
        Get comprehensive session information.

        Returns:
            dict: Session information dictionary
        """
        return {
            'is_authenticated': self.is_authenticated(),
            'username': self.get_username(),
            'login_time': self.get_login_time().isoformat() if self.get_login_time() else None,
            'session_duration': self.get_session_duration(),
            'remaining_minutes': self.get_session_remaining_time(),
            'language_preference': self.get_language_preference(),
            'camera_permissions': self.auth_state.camera_permissions.copy(),
            'is_expiring_soon': self.is_session_expiring_soon()
        }


class SessionEventHandler:
    """
    Handles session-related events and notifications.

    Provides event handling for session expiration, warnings,
    and other session management events.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize session event handler.

        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager
        self._warning_callbacks = []
        self._expiry_callbacks = []

    def add_warning_callback(self, callback):
        """
        Add callback for session expiration warnings.

        Args:
            callback: Function to call when session is expiring soon
        """
        self._warning_callbacks.append(callback)

    def add_expiry_callback(self, callback):
        """
        Add callback for session expiration.

        Args:
            callback: Function to call when session expires
        """
        self._expiry_callbacks.append(callback)

    def check_session_status(self) -> None:
        """Check session status and trigger appropriate callbacks."""
        if not self.session_manager.is_authenticated():
            return

        # Check for expiration warnings
        if self.session_manager.is_session_expiring_soon():
            remaining = self.session_manager.get_session_remaining_time()
            for callback in self._warning_callbacks:
                try:
                    callback(remaining)
                except Exception as e:
                    logger.error(f"Session warning callback error: {e}")

        # Check for session expiration
        if not self.session_manager.auth_state.is_session_valid():
            for callback in self._expiry_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Session expiry callback error: {e}")

            # Clear expired session
            self.session_manager.logout()
