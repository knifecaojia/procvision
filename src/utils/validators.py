"""
Input validation utilities for industrial vision application.

Provides comprehensive validation for usernames, passwords,
and other user inputs with proper error handling.
"""

import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class InputValidator:
    """
    Comprehensive input validation for the industrial vision application.

    Provides validation methods for usernames, passwords,
    and other user-facing inputs with detailed error messages.
    """

    # Username validation patterns
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
    RESERVED_USERNAMES = {
        'administrator', 'root', 'system', 'guest', 'user',
        'test', 'demo', 'api', 'service', 'null', 'undefined'
    }

    # Password validation patterns
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    COMMON_PASSWORDS = {
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey'
    }

    # Language validation
    SUPPORTED_LANGUAGES = ['中', 'English']

    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, Optional[str]]:
        """
        Validate username according to industrial standards.

        Args:
            username: Username to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Check for empty username
            if not username:
                return False, "Username cannot be empty"

            # Check for whitespace
            if username.strip() != username:
                return False, "Username cannot contain leading or trailing spaces"

            # Check length
            if len(username) < 3:
                return False, "Username must be at least 3 characters long"

            if len(username) > 50:
                return False, "Username cannot exceed 50 characters"

            # Check pattern
            if not cls.USERNAME_PATTERN.match(username):
                return False, "Username can only contain letters, numbers, underscores, and hyphens"

            # Check for reserved usernames
            if username.lower() in cls.RESERVED_USERNAMES:
                return False, "Username is reserved and cannot be used"

            # Check for consecutive special characters
            if '--' in username or '__' in username:
                return False, "Username cannot contain consecutive special characters"

            # Check for starting/ending with special characters
            if username.startswith(('-', '_')) or username.endswith(('-', '_')):
                return False, "Username cannot start or end with special characters"

            return True, None

        except Exception as e:
            logger.error(f"Username validation error: {e}")
            return False, "Username validation failed"

    @classmethod
    def validate_password(cls, password: str, username: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate password according to security standards.

        Args:
            password: Password to validate
            username: Username to check against (for similarity checks)

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Check for empty password
            if not password:
                return False, "Password cannot be empty"

            # Check length
            if len(password) < cls.PASSWORD_MIN_LENGTH:
                return False, f"Password must be at least {cls.PASSWORD_MIN_LENGTH} characters long"

            if len(password) > cls.PASSWORD_MAX_LENGTH:
                return False, f"Password cannot exceed {cls.PASSWORD_MAX_LENGTH} characters"

            # Check for whitespace
            if ' ' in password:
                return False, "Password cannot contain spaces"

            # Check for common passwords
            if password.lower() in cls.COMMON_PASSWORDS:
                return False, "Password is too common and not secure"

            # Check for similarity with username
            if username and cls._password_similar_to_username(password, username):
                return False, "Password cannot be similar to username"

            # Password strength indicators (not required, but recommended)
            strength_issues = []

            if not re.search(r'[a-z]', password):
                strength_issues.append("lowercase letter")

            if not re.search(r'[A-Z]', password):
                strength_issues.append("uppercase letter")

            if not re.search(r'\d', password):
                strength_issues.append("number")

            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                strength_issues.append("special character")

            # Only warn about strength issues, don't fail validation
            if strength_issues:
                logger.info(f"Password could be stronger: missing {', '.join(strength_issues)}")

            return True, None

        except Exception as e:
            logger.error(f"Password validation error: {e}")
            return False, "Password validation failed"

    @classmethod
    def validate_language(cls, language: str) -> Tuple[bool, Optional[str]]:
        """
        Validate language preference.

        Args:
            language: Language code to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            if not language:
                return False, "Language preference cannot be empty"

            if language not in cls.SUPPORTED_LANGUAGES:
                return False, f"Language must be one of: {', '.join(cls.SUPPORTED_LANGUAGES)}"

            return True, None

        except Exception as e:
            logger.error(f"Language validation error: {e}")
            return False, "Language validation failed"

    @classmethod
    def validate_session_token(cls, token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate session token format.

        Args:
            token: Session token to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            if not token:
                return False, "Session token cannot be empty"

            if len(token) < 16:
                return False, "Invalid session token format"

            # Basic format check for URL-safe base64 tokens
            if not re.match(r'^[A-Za-z0-9_-]+$', token):
                return False, "Invalid session token format"

            return True, None

        except Exception as e:
            logger.error(f"Session token validation error: {e}")
            return False, "Session token validation failed"

    @classmethod
    def validate_ip_address(cls, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Validate IP address format.

        Args:
            ip_address: IP address to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            if not ip_address:
                return True, None  # IP address is optional

            # IPv4 validation
            ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
            if ipv4_pattern.match(ip_address):
                parts = ip_address.split('.')
                for part in parts:
                    if int(part) > 255:
                        return False, "Invalid IP address"
                return True, None

            # IPv6 validation (basic)
            ipv6_pattern = re.compile(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$')
            if ipv6_pattern.match(ip_address):
                return True, None

            return False, "Invalid IP address format"

        except Exception as e:
            logger.error(f"IP address validation error: {e}")
            return False, "IP address validation failed"

    @classmethod
    def validate_user_agent(cls, user_agent: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user agent string.

        Args:
            user_agent: User agent string to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            if not user_agent:
                return True, None  # User agent is optional

            if len(user_agent) > 500:
                return False, "User agent string too long"

            # Check for potentially malicious content
            dangerous_patterns = [
                r'<script',
                r'javascript:',
                r'vbscript:',
                r'onload=',
                r'onerror='
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    return False, "Invalid user agent format"

            return True, None

        except Exception as e:
            logger.error(f"User agent validation error: {e}")
            return False, "User agent validation failed"

    @classmethod
    def _password_similar_to_username(cls, password: str, username: str) -> bool:
        """
        Check if password is too similar to username.

        Args:
            password: Password to check
            username: Username to compare against

        Returns:
            bool: True if password is too similar to username
        """
        try:
            password_lower = password.lower()
            username_lower = username.lower()

            # Check if password contains username
            if username_lower in password_lower:
                return True

            # Check if username contains password
            if password_lower in username_lower:
                return True

            # Check for simple reversals
            if password_lower == username_lower[::-1]:
                return True

            # Check for high similarity (Levenshtein distance would be better)
            if abs(len(password) - len(username)) <= 2:
                common_chars = set(password_lower) & set(username_lower)
                if len(common_chars) / max(len(set(password_lower)), len(set(username_lower))) > 0.7:
                    return True

            return False

        except Exception:
            return False

    @classmethod
    def sanitize_input(cls, input_string: str, max_length: int = 1000) -> str:
        """
        Sanitize user input for logging and display.

        Args:
            input_string: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            str: Sanitized string
        """
        try:
            if not input_string:
                return ""

            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\']', '', input_string)

            # Truncate to max length
            if len(sanitized) > max_length:
                sanitized = sanitized[:max_length] + "..."

            return sanitized.strip()

        except Exception:
            return "[Invalid Input]"


class ValidationRules:
    """
    Predefined validation rule sets for common use cases.

    Provides reusable validation rule combinations for different
    validation scenarios in the industrial vision application.
    """

    @staticmethod
    def login_form_rules() -> dict:
        """Get validation rules for login form."""
        return {
            'username': {
                'required': True,
                'min_length': 3,
                'max_length': 50,
                'pattern': r'^[a-zA-Z0-9_-]+$',
                'reserved': InputValidator.RESERVED_USERNAMES
            },
            'password': {
                'required': True,
                'min_length': InputValidator.PASSWORD_MIN_LENGTH,
                'max_length': InputValidator.PASSWORD_MAX_LENGTH,
                'no_spaces': True
            }
        }

    @staticmethod
    def user_creation_rules() -> dict:
        """Get validation rules for user creation."""
        rules = ValidationRules.login_form_rules()
        rules['password']['strength_check'] = True
        return rules

    @staticmethod
    def user_preference_rules() -> dict:
        """Get validation rules for user preferences."""
        return {
            'language': {
                'required': True,
                'allowed_values': InputValidator.SUPPORTED_LANGUAGES
            },
            'remember_username': {
                'required': False,
                'type': 'boolean'
            }
        }