"""
Core application functionality for industrial vision system.

Provides main application class, session management,
configuration, and core services.
"""

from .app import IndustrialVisionApp
from .session import SessionManager
from .config import AppConfig

__all__ = ['IndustrialVisionApp', 'SessionManager', 'AppConfig']