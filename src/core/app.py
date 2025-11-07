"""
Main application entry point for industrial vision system.

Provides the core application class that manages initialization,
session state, and window management for the industrial vision application.
"""

import sys
import logging
from pathlib import Path

# Setup logging before importing other modules
def setup_logging():
    """Configure application logging."""
    from .config import get_config

    config = get_config()
    log_config = config.logging

    # Create logs directory
    log_file = Path(log_config.file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_config.level.upper()),
        format=log_config.format,
        handlers=[
            logging.StreamHandler() if log_config.console_enabled else None,
            logging.FileHandler(log_config.file_path) if log_config.file_enabled else None
        ]
    )

    # Remove None handlers
    logger = logging.getLogger()
    logger.handlers = [h for h in logger.handlers if h is not None]


class IndustrialVisionApp:
    """
    Main application class for the industrial vision system.

    Manages application lifecycle, session state, and window management
    with proper initialization and cleanup procedures.
    """

    def __init__(self):
        """Initialize the industrial vision application."""
        # Setup logging first
        setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize PySide6 application
        try:
            from PySide6.QtWidgets import QApplication
            self.app = QApplication(sys.argv)
            self.app.setStyle("Fusion")

            # Set application properties
            self.app.setApplicationName("SMART-VISION")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("Industrial Vision Systems")

            self.logger.info("PySide6 application initialized successfully")

        except ImportError as e:
            self.logger.error(f"Failed to initialize PySide6: {e}")
            raise

        # Load configuration
        try:
            from .config import get_config
            self.config = get_config()
            self.logger.info("Configuration loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

        # Initialize session manager
        try:
            try:
                from .session import SessionManager
                from ..auth.services import AuthService
            except ImportError:
                from src.core.session import SessionManager
                from src.auth.services import AuthService

            auth_service = AuthService()
            self.session_manager = SessionManager(auth_service)
            self.auth_service = auth_service
            self.logger.info("Session manager initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize session manager: {e}")
            raise

        # Initialize windows
        self.login_window = None
        self.main_window = None

        # Setup cleanup handlers
        self.setup_cleanup_handlers()

    def setup_cleanup_handlers(self):
        """Setup cleanup handlers for proper application shutdown."""
        try:
            import atexit
            atexit.register(self.cleanup)

            # Handle Qt application events
            self.app.aboutToQuit.connect(self.cleanup)

            self.logger.debug("Cleanup handlers configured")

        except Exception as e:
            self.logger.warning(f"Failed to setup cleanup handlers: {e}")

    def initialize_windows(self):
        """Initialize application windows based on session state."""
        try:
            # Check if there's an active session
            if self.session_manager.is_authenticated() and self.session_manager.check_session_validity():
                # Go directly to main window
                self.logger.info("Active session found, showing main window")
                self.show_main_window()
            else:
                # Show login window
                self.logger.info("No active session, showing login window")
                self.show_login_window()

        except Exception as e:
            self.logger.error(f"Failed to initialize windows: {e}")
            # Fallback to login window
            self.show_login_window()

    def show_login_window(self):
        """Show the login window."""
        try:
            try:
                from ..ui.login_window import LoginWindow
            except ImportError:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from src.ui.login_window import LoginWindow

            # Close main window if it exists
            if self.main_window:
                self.main_window.close()
                self.main_window = None

            # Create and show login window
            self.login_window = LoginWindow(self.session_manager)
            self.login_window.show()

            self.logger.info("Login window displayed")

        except Exception as e:
            self.logger.error(f"Failed to show login window: {e}")
            raise

    def show_main_window(self):
        """Show the main application window."""
        try:
            try:
                from ..ui.main_window import MainWindow
            except ImportError:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from src.ui.main_window import MainWindow

            # Close login window if it exists
            if self.login_window:
                self.login_window.close()
                self.login_window = None

            # Create and show main window
            self.main_window = MainWindow(self.session_manager)
            self.main_window.show()

            self.logger.info("Main window displayed")

        except Exception as e:
            self.logger.error(f"Failed to show main window: {e}")
            raise

    def run(self) -> int:
        """
        Run the application main loop.

        Returns:
            int: Application exit code
        """
        try:
            self.logger.info("Starting Industrial Vision Application")

            # Initialize windows
            self.initialize_windows()

            # Start event loop
            exit_code = self.app.exec()

            self.logger.info(f"Application exited with code: {exit_code}")
            return exit_code

        except Exception as e:
            self.logger.error(f"Application runtime error: {e}")
            return 1

    def cleanup(self):
        """Perform application cleanup before exit."""
        try:
            self.logger.info("Performing application cleanup")

            # Cleanup session
            if hasattr(self, 'session_manager') and self.session_manager:
                self.session_manager.logout()

            # Cleanup windows
            if hasattr(self, 'login_window') and self.login_window:
                self.login_window.close()

            if hasattr(self, 'main_window') and self.main_window:
                self.main_window.close()

            # Save configuration
            try:
                from .config import save_config
                save_config()
                self.logger.debug("Configuration saved")
            except Exception as e:
                self.logger.warning(f"Failed to save configuration: {e}")

            self.logger.info("Application cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_application_info(self) -> dict:
        """
        Get application information.

        Returns:
            dict: Application information
        """
        return {
            'name': self.config.app_name,
            'version': self.config.app_version,
            'title': self.config.app_title,
            'debug_mode': self.config.debug_mode,
            'session_active': self.session_manager.is_authenticated() if self.session_manager else False,
            'current_user': self.session_manager.get_username() if self.session_manager else None
        }


def main():
    """
    Main entry point for the industrial vision application.

    Returns:
        int: Application exit code
    """
    try:
        # Create and run application
        app = IndustrialVisionApp()
        return app.run()

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0

    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())