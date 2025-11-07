# Implementation Quickstart Guide

**Date**: 2025-11-06
**Feature**: Create Login Flow with Main Page Navigation

## Getting Started

This guide provides the essential steps to implement the login flow and main page navigation for the industrial vision application using the current PySide6 tech stack.

## Prerequisites

Ensure you have the current development environment:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Implementation Steps

### Step 1: Create Project Structure

Create the modular directory structure as defined in the plan:

```bash
mkdir -p src/{auth,ui/{components,styles},core,utils}
mkdir -p tests/{unit,integration,fixtures}
touch src/__init__.py src/auth/__init__.py src/ui/__init__.py
touch src/ui/components/__init__.py src/ui/styles/__init__.py
touch src/core/__init__.py src/utils/__init__.py
```

### Step 2: Implement Authentication Core

Create the authentication service (`src/auth/services.py`):

```python
import bcrypt
import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

class AuthService:
    def __init__(self, db_path: str = "data/auth.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT 1,
                remember_username BOOLEAN DEFAULT 0,
                language_preference TEXT DEFAULT '中'
            )
        ''')

        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                ip_address TEXT NULL,
                user_agent TEXT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()

    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Authenticate user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id, password_hash, is_active FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return False, "Invalid username or password"

        user_id, password_hash, is_active = result

        if not is_active:
            return False, "Account is inactive"

        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            # Update last login
            self._update_last_login(user_id)
            return True, None
        else:
            return False, "Invalid username or password"

    def create_session(self, user_id: int) -> str:
        """Create new authentication session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=8)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO auth_sessions (session_id, user_id, expires_at)
            VALUES (?, ?, ?)
        ''', (session_id, user_id, expires_at))

        conn.commit()
        conn.close()

        return session_id

    def _update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                      (datetime.now(), user_id))
        conn.commit()
        conn.close()
```

### Step 3: Enhance Login Window

Enhance the existing `login_page.py` by integrating authentication:

```python
# In login_page.py, modify the LoginWindow class

from src.auth.services import AuthService
from src.core.session import SessionManager

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing initialization code ...

        # Add authentication components
        self.auth_service = AuthService()
        self.session_manager = SessionManager()

    def on_login_clicked(self):
        """Enhanced login handler with actual authentication"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember_me = self.remember_checkbox.isChecked()
        language = self.lang_combo.currentText()

        # Clear previous error states
        self._clear_error_states()

        # Validate input
        if not username or not password:
            self._show_error("Please enter username and password")
            return

        # Show loading state
        self._set_loading_state(True)

        # Authenticate user
        success, error_msg = self.auth_service.authenticate_user(username, password)

        if success:
            # Create session
            user_id = self.auth_service.get_user_id(username)
            session_token = self.auth_service.create_session(user_id)

            # Update session manager
            self.session_manager.set_authenticated_session(username, session_token)

            # Save preferences
            if remember_me:
                self._save_user_preferences(username, language)

            # Navigate to main window
            self._navigate_to_main_window()
        else:
            self._show_error(error_msg)

        self._set_loading_state(False)

    def _clear_error_states(self):
        """Clear any previous error indicators"""
        self.username_input.setStyleSheet("")
        self.password_input.setStyleSheet("")

    def _show_error(self, message: str):
        """Display error message to user"""
        # You can implement a status label or message box
        self.password_input.setStyleSheet("border: 1px solid #E85454;")
        print(f"Login error: {message}")  # Replace with proper UI feedback

    def _set_loading_state(self, loading: bool):
        """Set loading state for UI elements"""
        self.login_button.setEnabled(not loading)
        self.login_button.setText("AUTHENTICATING..." if loading else "LOGIN")

    def _navigate_to_main_window(self):
        """Navigate to main application window"""
        # Hide login window
        self.hide()

        # Create and show main window
        from src.ui.main_window import MainWindow
        self.main_window = MainWindow(self.session_manager)
        self.main_window.show()
```

### Step 4: Create Main Window

Create the main application window (`src/ui/main_window.py`):

```python
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.setWindowTitle("SMART-VISION MAIN")
        self.setFixedSize(1200, 700)

        # Apply existing color scheme
        self.colors = {
            'deep_graphite': '#1A1D23',
            'steel_grey': '#1F232B',
            'arctic_white': '#F2F4F8',
            'cool_grey': '#8C92A0',
            'hover_orange': '#FF8C32',
        }

        self.init_ui()
        self.setup_style()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header with user info and logout
        header = self.create_header()
        layout.addWidget(header)

        # Main content area
        content = self.create_content_area()
        layout.addWidget(content)

    def create_header(self):
        """Create header with user info and logout"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        # Welcome message
        welcome_label = QLabel(f"Welcome, {self.session_manager.get_username()}")
        welcome_label.setStyleSheet(f"color: {self.colors['arctic_white']}; font-size: 18px;")

        # Logout button
        logout_button = QPushButton("LOGOUT")
        logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['hover_orange']};
                color: {self.colors['arctic_white']};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FFB347;
            }}
        """)
        logout_button.clicked.connect(self.on_logout)

        header_layout.addWidget(welcome_label)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)

        return header_widget

    def create_content_area(self):
        """Create main content area"""
        content = QWidget()
        content.setStyleSheet(f"background-color: {self.colors['steel_grey']}; border-radius: 8px;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)

        # Main page title
        title = QLabel("INDUSTRIAL VISION SYSTEM")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {self.colors['arctic_white']};
            font-size: 32px;
            font-weight: bold;
            margin: 40px 0;
        """)

        # Placeholder content
        placeholder = QLabel("Main application content will be displayed here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {self.colors['cool_grey']}; font-size: 16px;")

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(placeholder)
        layout.addStretch()

        return content

    def setup_style(self):
        """Apply main window styling"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['deep_graphite']};
            }}
        """)

    def on_logout(self):
        """Handle logout action"""
        self.session_manager.logout()
        self.close()

        # Show login window again
        from src.ui.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
```

### Step 5: Create Session Manager

Create session management (`src/core/session.py`):

```python
from datetime import datetime, timedelta
from typing import Optional

class SessionManager:
    def __init__(self):
        self.username: Optional[str] = None
        self.session_token: Optional[str] = None
        self.login_time: Optional[datetime] = None
        self.expires_at: Optional[datetime] = None

    def set_authenticated_session(self, username: str, session_token: str):
        """Set authenticated session data"""
        self.username = username
        self.session_token = session_token
        self.login_time = datetime.now()
        self.expires_at = self.login_time + timedelta(hours=8)

    def is_authenticated(self) -> bool:
        """Check if user is authenticated and session is valid"""
        if not self.session_token or not self.expires_at:
            return False

        return datetime.now() < self.expires_at

    def get_username(self) -> Optional[str]:
        """Get current username"""
        return self.username

    def get_session_token(self) -> Optional[str]:
        """Get current session token"""
        return self.session_token

    def logout(self):
        """Clear session data"""
        self.username = None
        self.session_token = None
        self.login_time = None
        self.expires_at = None

    def extend_session(self, hours: int = 8):
        """Extend session expiration"""
        if self.is_authenticated():
            self.expires_at = datetime.now() + timedelta(hours=hours)
```

### Step 6: Update Main Application Entry

Create main application entry point (`src/core/app.py`):

```python
import sys
from PySide6.QtWidgets import QApplication
from src.ui.login_window import LoginWindow
from src.core.session import SessionManager

class IndustrialVisionApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.session_manager = SessionManager()
        self.app.setStyle("Fusion")

    def run(self):
        """Start the application"""
        # Check for existing session
        if self.session_manager.is_authenticated():
            # Go directly to main window
            from src.ui.main_window import MainWindow
            main_window = MainWindow(self.session_manager)
            main_window.show()
        else:
            # Show login window
            login_window = LoginWindow()
            login_window.show()

        return self.app.exec()

def main():
    app = IndustrialVisionApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
```

### Step 7: Create Default User

Create a script to create a default user for testing:

```python
# scripts/create_default_user.py
import bcrypt
import sqlite3
import os

def create_default_user():
    """Create a default admin user for testing"""
    db_path = "data/auth.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT 1,
            remember_username BOOLEAN DEFAULT 0,
            language_preference TEXT DEFAULT '中'
        )
    ''')

    # Create default admin user
    username = "admin"
    password = "admin123"  # Change this in production!
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

    try:
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      (username, password_hash.decode('utf-8')))
        conn.commit()
        print(f"Default user '{username}' created successfully")
        print(f"Password: {password}")
        print("Please change the default password in production!")
    except sqlite3.IntegrityError:
        print(f"User '{username}' already exists")

    conn.close()

if __name__ == "__main__":
    create_default_user()
```

## Testing the Implementation

1. **Create default user**:
   ```bash
   python scripts/create_default_user.py
   ```

2. **Run the application**:
   ```bash
   python src/core/app.py
   ```

3. **Test login flow**:
   - Use username: `admin`, password: `admin123`
   - Verify successful navigation to main page
   - Test logout functionality
   - Test session persistence

## Next Steps

1. **Add comprehensive error handling** and user feedback
2. **Implement input validation** with proper visual feedback
3. **Add user management** features for production use
4. **Implement proper logging** for security and debugging
5. **Add camera integration** to the main window
6. **Create unit and integration tests** for all components

This implementation provides a solid foundation for the login flow while maintaining the existing industrial UI design standards and adding robust authentication capabilities.