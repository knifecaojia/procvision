# Data Model Design

**Date**: 2025-11-06
**Feature**: Create Login Flow with Main Page Navigation

## Core Entities

### User Entity

Represents authenticated users in the industrial vision system.

```python
class User:
    """
    User entity for authentication and session management
    """
    def __init__(self):
        self.id: int = None                    # Primary key
        self.username: str = None              # Unique username
        self.password_hash: str = None         # bcrypt hashed password
        self.created_at: datetime = None       # Account creation timestamp
        self.last_login: datetime = None       # Last successful login
        self.is_active: bool = True            # Account status
        self.remember_username: bool = False   # Remember me preference
        self.language_preference: str = "中"    # UI language (中/English)
```

**Database Schema**:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT 1,
    remember_username BOOLEAN DEFAULT 0,
    language_preference TEXT DEFAULT '中'
);
```

**Validation Rules**:
- Username: 3-50 characters, alphanumeric + underscore
- Password: Minimum 8 characters (complexity enforced at UI level)
- Language: "中" or "English" only

### Authentication Session Entity

Manages user session state and authentication tokens.

```python
class AuthSession:
    """
    Session entity for maintaining login state
    """
    def __init__(self):
        self.session_id: str = None            # Unique session identifier
        self.user_id: int = None               # Foreign key to User
        self.created_at: datetime = None       # Session creation
        self.expires_at: datetime = None       # Session expiration
        self.is_active: bool = True            # Session status
        self.ip_address: str = None            # Client IP (if available)
        self.user_agent: str = None            # Client info
```

**Database Schema**:
```sql
CREATE TABLE auth_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    ip_address TEXT NULL,
    user_agent TEXT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Authentication State Entity

Tracks current application authentication state.

```python
class AuthState:
    """
    Current authentication state for the application
    """
    def __init__(self):
        self.is_authenticated: bool = False    # Current login status
        self.current_user: User = None         # Logged-in user object
        self.session_token: str = None         # Active session token
        self.login_time: datetime = None       # When user logged in
        self.session_expires: datetime = None  # When session expires
        self.camera_permissions: dict = {}     # Camera access permissions
```

## Entity Relationships

```
User (1) -----> (N) AuthSession
User (1) -----> (1) AuthState (runtime)
```

## State Transitions

### Authentication State Machine

```
[UNAUTHENTICATED] --login_success--> [AUTHENTICATED]
     ^                              |
     |                              | logout/session_expire
     +------------------------------+
```

### Login Flow States

1. **Initial State**: User not authenticated, showing login page
2. **Validation State**: Validating user credentials
3. **Success State**: Credentials valid, redirecting to main page
4. **Error State**: Invalid credentials, showing error message
5. **Authenticated State**: User logged in, main page displayed

### Session Management States

1. **Active**: Session is valid and user is authenticated
2. **Expired**: Session has expired, user must re-authenticate
3. **Terminated**: User logged out or session was terminated

## Data Integrity Constraints

### User Constraints
- Username must be unique
- Password hash is required (bcrypt format)
- Email format validation (if email is used as username)
- Active flag controls login access

### Session Constraints
- Session ID must be unique
- Expiration time must be in the future
- User ID must reference existing user
- Active sessions limited per user (configurable)

### Security Constraints
- Passwords never stored in plain text
- Session tokens generated using cryptographically secure random
- All timestamps stored in UTC
- Failed login attempts tracked (audit capability)

## Performance Considerations

### Database Indexes
```sql
-- Optimized queries for authentication
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX idx_sessions_active ON auth_sessions(is_active, expires_at);
```

### Session Cleanup
- Automatic cleanup of expired sessions
- Background task to remove old session data
- Configurable session timeout (default: 8 hours)

### Memory Management
- User objects cached during session
- Minimal session data stored in memory
- Lazy loading of user preferences