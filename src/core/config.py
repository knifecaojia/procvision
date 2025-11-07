"""
Configuration management for industrial vision application.

Provides centralized configuration handling with support for
environment variables, config files, and default values.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Authentication configuration settings."""

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
    supported_languages: list = field(default_factory=lambda: ["中", "English"])
    remember_username_default: bool = False

    # Session settings
    max_sessions_per_user: int = 3
    session_cleanup_interval_minutes: int = 30


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    # SQLite settings
    database_path: str = "data/auth.db"
    connection_timeout: int = 30
    enable_wal_mode: bool = True
    foreign_keys_enabled: bool = True

    # Backup settings
    auto_backup: bool = True
    backup_directory: str = "data/backups"
    backup_retention_days: int = 30


@dataclass
class UIConfig:
    """User interface configuration settings."""

    # Window settings
    window_width: int = 1050
    window_height: int = 700
    window_resizable: bool = False
    frameless_window: bool = True

    # Color scheme (industrial theme)
    colors: Dict[str, str] = field(default_factory=lambda: {
        'deep_graphite': '#1A1D23',
        'steel_grey': '#1F232B',
        'dark_border': '#242831',
        'arctic_white': '#F2F4F8',
        'cool_grey': '#8C92A0',
        'hover_orange': '#FF8C32',
        'amber': '#FFAC54',
        'icon_neutral': '#D7DCE6',
        'success_green': '#3CC37A',
        'error_red': '#E85454',
        'warning_yellow': '#FFB347',
        'title_bar_dark': '#15181E'  # 更深的标题栏颜色
    })

    # Typography
    font_family: str = "Arial"
    base_font_size: int = 12
    title_font_size: int = 24
    small_font_size: int = 10

    # Animation and transitions
    enable_animations: bool = True
    animation_duration_ms: int = 200


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/app.log"
    file_max_size_mb: int = 10
    file_backup_count: int = 5
    console_enabled: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""

    auth: AuthConfig = field(default_factory=AuthConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Application metadata
    app_name: str = "SMART-VISION"
    app_version: str = "1.0.0"
    app_title: str = "Industrial Vision System"

    # Development settings
    debug_mode: bool = False
    dev_mode: bool = False
    config_file_path: str = "config/app_config.json"


class ConfigManager:
    """
    Configuration manager for the industrial vision application.

    Handles loading, saving, and managing configuration from various sources.
    """

    def __init__(self, config_file_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file_path: Path to configuration file
        """
        self.config_file_path = config_file_path or "config/app_config.json"
        self.config = AppConfig()
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from file and environment variables."""
        # Load from file if exists
        self._load_from_file()

        # Override with environment variables
        self._load_from_environment()

        # Ensure directories exist
        self._ensure_directories()

    def _load_from_file(self):
        """Load configuration from JSON file."""
        try:
            config_path = Path(self.config_file_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Update configuration with loaded data
                self._update_config_from_dict(config_data)
                logger.info(f"Configuration loaded from: {self.config_file_path}")
            else:
                logger.info("Configuration file not found, using defaults")
                self._save_configuration()  # Save default configuration

        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            logger.info("Using default configuration")

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'SMART_VISION_DEBUG': ('debug_mode', bool),
            'SMART_VISION_DEV_MODE': ('dev_mode', bool),
            'SMART_VISION_DB_PATH': ('database.database_path', str),
            'SMART_VISION_LOG_LEVEL': ('logging.level', str),
            'SMART_VISION_SESSION_TIMEOUT': ('auth.session_timeout_hours', int),
            'SMART_VISION_LANGUAGE': ('auth.default_language', str),
        }

        for env_var, (config_path, value_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if value_type == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        value = int(value)
                    else:
                        value = str(value)

                    self._set_nested_value(config_path, value)
                    logger.info(f"Environment variable applied: {env_var}")

                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid environment variable {env_var}: {e}")

    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration object from dictionary."""
        if 'auth' in config_data:
            self._update_dataclass(self.config.auth, config_data['auth'])

        if 'database' in config_data:
            self._update_dataclass(self.config.database, config_data['database'])

        if 'ui' in config_data:
            self._update_dataclass(self.config.ui, config_data['ui'])

        if 'logging' in config_data:
            self._update_dataclass(self.config.logging, config_data['logging'])

        # Update root level properties
        for key in ['app_name', 'app_version', 'app_title', 'debug_mode', 'dev_mode']:
            if key in config_data:
                setattr(self.config, key, config_data[key])

    def _update_dataclass(self, dataclass_instance, data: Dict[str, Any]):
        """Update dataclass instance with dictionary data."""
        for key, value in data.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)

    def _set_nested_value(self, path: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = path.split('.')
        obj = self.config

        for key in keys[:-1]:
            obj = getattr(obj, key)

        setattr(obj, keys[-1], value)

    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            os.path.dirname(self.config.database.database_path),
            self.config.database.backup_directory,
            os.path.dirname(self.config.logging.file_path),
            os.path.dirname(self.config_file_path)
        ]

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)

    def save_configuration(self):
        """Save current configuration to file."""
        try:
            config_data = {
                'auth': self._dataclass_to_dict(self.config.auth),
                'database': self._dataclass_to_dict(self.config.database),
                'ui': self._dataclass_to_dict(self.config.ui),
                'logging': self._dataclass_to_dict(self.config.logging),
                'app_name': self.config.app_name,
                'app_version': self.config.app_version,
                'app_title': self.config.app_title,
                'debug_mode': self.config.debug_mode,
                'dev_mode': self.config.dev_mode
            }

            config_path = Path(self.config_file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Configuration saved to: {self.config_file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def _dataclass_to_dict(self, dataclass_instance) -> Dict[str, Any]:
        """Convert dataclass instance to dictionary."""
        if hasattr(dataclass_instance, '__dict__'):
            result = {}
            for key, value in dataclass_instance.__dict__.items():
                if hasattr(value, '__dict__'):
                    result[key] = self._dataclass_to_dict(value)
                else:
                    result[key] = value
            return result
        return dataclass_instance

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        return self.config

    def reload_configuration(self):
        """Reload configuration from file."""
        self.config = AppConfig()
        self._load_configuration()
        logger.info("Configuration reloaded")


# Global configuration instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get current application configuration."""
    return get_config_manager().get_config()


def save_config():
    """Save current configuration to file."""
    get_config_manager().save_configuration()


def reload_config():
    """Reload configuration from file."""
    get_config_manager().reload_configuration()