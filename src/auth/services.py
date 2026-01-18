"""
Authentication services for industrial vision application.

Provides secure user authentication, session management,
and credential validation for industrial environments.
"""

import bcrypt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from .models import User, AuthSession, AuthState
from .storage import UserStorage, SessionStorage
from ..services.network_service import NetworkService

logger = logging.getLogger(__name__)


class AuthService:
    """
    Core authentication service for the industrial vision application.

    Handles user authentication, session management, and security
    operations with proper error handling and logging.
    """

    def __init__(self, db_path: str = "data/auth.db"):
        self.user_storage = UserStorage(db_path)
        self.session_storage = SessionStorage(db_path)
        self.auth_state = AuthState()
        self.network_service = NetworkService()

        # Security configuration
        self.bcrypt_cost = 12
        self.session_timeout_hours = 8
        self.max_sessions_per_user = 3

    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate user credentials with proper security validation.

        Args:
            username: User's username
            password: User's password (plaintext)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Input validation
            if not username or not password:
                return False, "Username and password are required"

            # Try network login
            network_success = False
            try:
                login_data = self.network_service.login(username, password)
                if login_data.get("code") == 200:
                    network_success = True
                    # Login successful
                    # Ensure user exists in local DB for preferences etc.
                    user_data = self.user_storage.get_user_by_username(username)
                    if not user_data:
                        # Create local user
                        # Use a dummy hash since we rely on network auth
                        dummy_hash = self._hash_password(password)
                        self.user_storage.create_user(username, dummy_hash)
                        user_data = self.user_storage.get_user_by_username(username)
                    
                    if user_data:
                         self.user_storage.update_last_login(user_data['id'])

                    logger.info(f"User authenticated successfully via network: {username}")
                    return True, None
            except Exception as e:
                 logger.warning(f"Network login failed: {e}")
                 # Continue to local fallback

            # Fallback to local storage if network fails or user not found on network
            # This allows offline login or dev/mock usage
            logger.info(f"Attempting local fallback login for: {username}")
            
            # Special handling for dev/admin in case it doesn't exist locally yet
            # and we are in a "first run" scenario where network is down.
            user_data = self.user_storage.get_user_by_username(username)
            
            # Auto-seed admin user for development convenience if not exists
            if not user_data and username == "admin" and password == "admin123":
                 logger.info("Seeding default admin user for local fallback")
                 password_hash = self._hash_password(password)
                 self.user_storage.create_user(username, password_hash)
                 user_data = self.user_storage.get_user_by_username(username)

            if not user_data:
                logger.warning(f"Authentication failed: User not found locally - {username}")
                return False, "Invalid username or password (Network unavailable)"

            password_hash = user_data.get('password_hash')
            if not password_hash:
                return False, "Authentication service unavailable"

            # Verify password using bcrypt
            if not self._verify_password(password, password_hash):
                logger.warning(f"Authentication failed: Invalid password - {username}")
                return False, "Invalid username or password"

            user = User.from_dict(dict(user_data))

            # Check if user account is active
            if not user.is_active:
                return False, "Account is inactive"

            # Update last login timestamp
            self.user_storage.update_last_login(user.id)

            logger.info(f"User authenticated successfully (Local): {username}")
            return True, None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, "Authentication service unavailable"

    def create_session(self, user_id: int, **kwargs) -> Optional[str]:
        """
        Create new authentication session with proper security.

        Args:
            user_id: ID of authenticated user
            **kwargs: Additional session data (ip_address, user_agent)

        Returns:
            Session token string or None if creation fails
        """
        try:
            # Generate secure session token
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=self.session_timeout_hours)

            # Clean up old sessions for this user
            self._cleanup_user_sessions(user_id)

            # Create session in storage
            success = self.session_storage.create_session(
                session_id=session_id,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent')
            )

            if success:
                logger.info(f"Session created for user ID: {user_id}")
                return session_id
            else:
                logger.error(f"Failed to create session for user ID: {user_id}")
                return None

        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None

    def validate_session(self, session_token: str) -> Optional[User]:
        """
        Validate session token and return user data.

        Args:
            session_token: Session token to validate

        Returns:
            User object if valid, None otherwise
        """
        try:
            if not session_token:
                return None

            # Retrieve session from storage
            session_data = self.session_storage.get_session(session_token)
            if not session_data:
                logger.warning(f"Session validation failed: Session not found")
                return None

            session = AuthSession.from_dict(session_data)

            # Check if session is still valid
            if not session.is_valid():
                logger.warning(f"Session validation failed: Session expired or inactive")
                return None

            # Retrieve user data
            user_data = self.user_storage.get_user_by_id(session.user_id)
            if not user_data:
                logger.warning(f"Session validation failed: User not found")
                return None

            user = User.from_dict(user_data)

            # Extend session if close to expiration
            if session.expires_at and session.expires_at < datetime.now() + timedelta(hours=1):
                session.extend_session()
                # Update storage (implementation needed in SessionStorage)
                logger.info(f"Session extended for user: {user.username}")

            return user

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None

    def logout(self, session_token: str) -> bool:
        """
        Terminate user session securely.

        Args:
            session_token: Session token to terminate

        Returns:
            True if session was terminated, False if not found
        """
        try:
            success = self.session_storage.delete_session(session_token)
            if success:
                logger.info("User logged out successfully")
            else:
                logger.warning("Logout failed: Session not found")
            return success

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions for security and maintenance.

        Returns:
            Number of sessions cleaned up
        """
        try:
            count = self.session_storage.cleanup_expired_sessions()
            return count

        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return 0

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by username.

        Args:
            username: Username to look up

        Returns:
            User data dictionary or None if not found
        """
        try:
            return self.user_storage.get_user_by_username(username)
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_id(self, username: str) -> Optional[int]:
        """
        Get user ID by username.

        Args:
            username: Username to look up

        Returns:
            User ID or None if not found
        """
        try:
            user_data = self.user_storage.get_user_by_username(username)
            return user_data['id'] if user_data else None

        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None

    def create_user(self, username: str, password: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Create new user account with secure password hashing.

        Args:
            username: Username for new account
            password: Plain text password
            **kwargs: Additional user data (language_preference, remember_username)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Validate input
            if not username or not password:
                return False, "Username and password are required"

            # Validate username format
            try:
                User(username=username).validate_username()
            except ValueError as e:
                return False, str(e)

            # Validate password strength
            if len(password) < 8:
                return False, "Password must be at least 8 characters long"

            # Hash password with bcrypt
            password_hash = self._hash_password(password)

            # Create user in storage
            success = self.user_storage.create_user(
                username=username,
                password_hash=password_hash,
                language_preference=kwargs.get('language_preference', '中'),
                remember_username=kwargs.get('remember_username', False)
            )

            if success:
                logger.info(f"User created successfully: {username}")
                return True, None
            else:
                return False, "Username already exists"

        except Exception as e:
            logger.error(f"User creation error: {e}")
            return False, "Failed to create user account"

    def update_user_preferences(self, username: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences.

        Args:
            username: Username to update
            preferences: Dictionary of preferences

        Returns:
            True if update successful
        """
        try:
            user_data = self.user_storage.get_user_by_username(username)
            if not user_data:
                return False

            return self.user_storage.update_user_preferences(user_data['id'], preferences)

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with proper security settings.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self.bcrypt_cost)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify password against bcrypt hash.

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches hash
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    def _cleanup_user_sessions(self, user_id: int) -> None:
        """
        Clean up old sessions for a user to maintain session limits.

        Args:
            user_id: User ID to clean up sessions for
        """
        # This would be implemented to maintain max_sessions_per_user limit
        # For now, we'll rely on the session cleanup mechanism
        pass


# Add get_user_by_username method to UserStorage (missing from storage.py)
def add_user_storage_method():
    """Add missing get_user_by_username method to UserStorage."""
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by username (already exists, just ensuring it's available)."""
        return self.get_user_by_username(username)

    # The method already exists in UserStorage, so no changes needed


class SessionManager:
    """
    High-level session management for the application.

    Provides simplified interface for managing authentication
    state and user sessions throughout the application.
    """

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def login(self, username: str, password: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Perform user login with session creation.

        Args:
            username: Username
            password: Password
            **kwargs: Additional login data

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Authenticate user
        success, error = self.auth_service.authenticate_user(username, password)
        if not success:
            return False, error

        # Get user ID
        user_id = self.auth_service.get_user_id(username)
        if not user_id:
            return False, "Failed to retrieve user information"

        # Create session
        session_token = self.auth_service.create_session(user_id, **kwargs)
        if not session_token:
            return False, "Failed to create session"

        # Update auth state
        user_data = self.auth_service.user_storage.get_user_by_username(username)
        user = User.from_dict(user_data)
        session_data = self.auth_service.session_storage.get_session(session_token)
        session = AuthSession.from_dict(session_data)

        self.auth_service.auth_state.set_authenticated(user, session_token, session.expires_at)

        return True, None

    def logout(self) -> bool:
        """
        Perform user logout.

        Returns:
            True if logout successful
        """
        session_token = self.auth_service.auth_state.session_token
        if not session_token:
            return False

        success = self.auth_service.logout(session_token)
        self.auth_service.auth_state.clear_authentication()
        return success

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self.auth_service.auth_state.is_authenticated

    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user."""
        return self.auth_service.auth_state.current_user

    def get_session_token(self) -> Optional[str]:
        """Get current session token."""
        return self.auth_service.auth_state.session_token

    def check_session_validity(self) -> bool:
        """Check if current session is still valid."""
        if not self.is_authenticated():
            return False

        session_token = self.get_session_token()
        if not session_token:
            self.auth_service.auth_state.clear_authentication()
            return False

        user = self.auth_service.validate_session(session_token)
        if not user:
            self.auth_service.auth_state.clear_authentication()
            return False

        return True

    def get_username(self) -> Optional[str]:
        """Get current username."""
        user = self.get_current_user()
        return user.username if user else None
