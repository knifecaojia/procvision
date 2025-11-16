"""
Database storage implementation for authentication system.

Provides SQLite-based storage for users and sessions with proper
initialization and management for industrial applications.
"""

import os
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages SQLite database connection with proper error handling."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Create database directory if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_script(self, script: str) -> bool:
        """Execute SQL script for database initialization."""
        try:
            conn = self.get_connection()
            conn.executescript(script)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database script execution failed: {e}")
            return False


class UserStorage:
    """User data storage and management."""

    def __init__(self, db_path: str = "data/auth.db"):
        self.db = DatabaseConnection(db_path)
        self._initialize_tables()

    def _initialize_tables(self):
        """Initialize user-related database tables."""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT 1,
            remember_username BOOLEAN DEFAULT 0,
            language_preference TEXT DEFAULT '中'
        );

        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
        """

        if not self.db.execute_script(schema):
            raise RuntimeError("Failed to initialize user tables")

    def create_user(self, username: str, password_hash: str, **kwargs) -> bool:
        """Create a new user account."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO users (username, password_hash, language_preference, remember_username)
                VALUES (?, ?, ?, ?)
            ''', (
                username,
                password_hash,
                kwargs.get('language_preference', '中'),
                kwargs.get('remember_username', False)
            ))

            conn.commit()
            conn.close()
            logger.info(f"User created successfully: {username}")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"User already exists: {username}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Failed to create user: {e}")
            return False

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by username."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, password_hash, created_at, last_login,
                       is_active, remember_username, language_preference
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve user: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user by ID."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, password_hash, created_at, last_login,
                       is_active, remember_username, language_preference
                FROM users WHERE id = ? AND is_active = 1
            ''', (user_id,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve user by ID: {e}")
            return None

    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now(), user_id))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to update last login: {e}")
            return False

    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            updates = []
            params = []

            if 'language_preference' in preferences:
                updates.append("language_preference = ?")
                params.append(preferences['language_preference'])

            if 'remember_username' in preferences:
                updates.append("remember_username = ?")
                params.append(preferences['remember_username'])

            if updates:
                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()

            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to update user preferences: {e}")
            return False


class SessionStorage:
    """Session data storage and management."""

    def __init__(self, db_path: str = "data/auth.db"):
        self.db = DatabaseConnection(db_path)
        self._initialize_tables()

    def _initialize_tables(self):
        """Initialize session-related database tables."""
        schema = """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            ip_address TEXT NULL,
            user_agent TEXT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON auth_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_active ON auth_sessions(is_active, expires_at);
        """

        if not self.db.execute_script(schema):
            raise RuntimeError("Failed to initialize session tables")

    def create_session(self, session_id: str, user_id: int, expires_at: datetime, **kwargs) -> bool:
        """Create a new authentication session."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO auth_sessions (session_id, user_id, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                user_id,
                expires_at,
                kwargs.get('ip_address'),
                kwargs.get('user_agent')
            ))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to create session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session by ID."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT session_id, user_id, created_at, expires_at, is_active, ip_address, user_agent
                FROM auth_sessions
                WHERE session_id = ? AND is_active = 1 AND expires_at > datetime('now')
            ''', (session_id,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session record."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE auth_sessions SET is_active = 0 WHERE session_id = ?
            ''', (session_id,))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE auth_sessions
                SET is_active = 0
                WHERE expires_at <= datetime('now') OR is_active = 0
            ''')

            count = cursor.rowcount
            conn.commit()
            conn.close()

            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")

            return count

        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0