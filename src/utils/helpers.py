"""
Helper functions for industrial vision application.

Provides UI helper functions and file utilities for
common operations throughout the application.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UIHelper:
    """User interface helper functions."""

    @staticmethod
    def format_error_message(message: str) -> str:
        """
        Format error message for display.

        Args:
            message: Error message to format

        Returns:
            Formatted error message
        """
        return f"错误: {message}" if not message.startswith("错误:") else message

    @staticmethod
    def format_success_message(message: str) -> str:
        """
        Format success message for display.

        Args:
            message: Success message to format

        Returns:
            Formatted success message
        """
        return f"成功: {message}" if not message.startswith("成功:") else message

    @staticmethod
    def get_status_color(is_success: bool) -> str:
        """
        Get color code for status.

        Args:
            is_success: Whether status is success

        Returns:
            Color code string
        """
        return "#3CC37A" if is_success else "#E85454"

    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    @staticmethod
    def center_text(text: str, width: int) -> str:
        """
        Center text within specified width.

        Args:
            text: Text to center
            width: Total width

        Returns:
            Centered text
        """
        return text.center(width)


class FileHelper:
    """File operation helper functions."""

    @staticmethod
    def ensure_directory(directory: Path) -> bool:
        """
        Ensure directory exists.

        Args:
            directory: Directory path

        Returns:
            True if directory exists or was created
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False

    @staticmethod
    def file_exists(file_path: Path) -> bool:
        """
        Check if file exists.

        Args:
            file_path: File path to check

        Returns:
            True if file exists
        """
        try:
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False

    @staticmethod
    def read_text_file(file_path: Path) -> Optional[str]:
        """
        Read text file content.

        Args:
            file_path: File path to read

        Returns:
            File content or None if failed
        """
        try:
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            return None
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    @staticmethod
    def write_text_file(file_path: Path, content: str) -> bool:
        """
        Write text file content.

        Args:
            file_path: File path to write
            content: Content to write

        Returns:
            True if successful
        """
        try:
            FileHelper.ensure_directory(file_path.parent)
            file_path.write_text(content, encoding='utf-8')
            logger.debug(f"File written: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False

    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: File path

        Returns:
            File size in bytes
        """
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.stat().st_size
            return 0
        except Exception:
            return 0

    @staticmethod
    def backup_file(file_path: Path, backup_suffix: str = ".bak") -> bool:
        """
        Create backup of file.

        Args:
            file_path: Original file path
            backup_suffix: Suffix for backup file

        Returns:
            True if backup created successfully
        """
        try:
            if file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
                import shutil
                shutil.copy2(file_path, backup_path)
                logger.info(f"Backup created: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
            return False