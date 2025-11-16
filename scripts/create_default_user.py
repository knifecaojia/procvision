"""
Create default user script for industrial vision application.

Creates a default admin user for testing and initial setup
of the industrial vision login system.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

try:
    from src.auth.services import AuthService
    from src.core.config import get_config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_default_user():
    """Create a default admin user for testing."""
    try:
        print("Creating default user for Industrial Vision Application...")
        print("=" * 60)

        # Initialize auth service
        auth_service = AuthService()

        # Default user credentials
        username = "admin"
        password = "admin123"  # Change this in production!
        language = "中"

        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Language: {language}")
        print()

        # Check if user already exists
        existing_user = auth_service.get_user_by_username(username)
        if existing_user:
            print(f"✓ User '{username}' already exists")
            print("  No action needed")
            return True

        # Create the user
        success, error = auth_service.create_user(
            username=username,
            password=password,
            language_preference=language,
            remember_username=False
        )

        if success:
            print(f"✓ Successfully created user '{username}'")
            print(f"  User ID: {auth_service.get_user_id(username)}")
            print()
            print("⚠️  IMPORTANT SECURITY NOTES:")
            print("  - This is a default password for testing only")
            print("  - Change this password in production environments")
            print("  - Use strong passwords for real users")
            print("  - Enable additional security features as needed")
            return True
        else:
            print(f"✗ Failed to create user: {error}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        print(f"✗ Error: {e}")
        return False


def verify_database():
    """Verify database is accessible."""
    try:
        config = get_config()
        db_path = Path(config.database.database_path)

        print(f"Database path: {db_path}")

        if db_path.exists():
            print("✓ Database file exists")
        else:
            print("✓ Database file will be created")

        return True

    except Exception as e:
        print(f"✗ Database verification failed: {e}")
        return False


def main():
    """Main function."""
    print("Industrial Vision Application - Default User Creation")
    print("=" * 60)

    # Verify database
    if not verify_database():
        print("Database verification failed. Exiting.")
        return 1

    print()

    # Create user
    if create_default_user():
        print("\n✓ Default user setup completed successfully!")
        print("\nYou can now run the application with:")
        print("  python src/core/app.py")
        print("\nOr use the existing login_page.py:")
        print("  python login_page.py")
        return 0
    else:
        print("\n✗ Failed to create default user")
        return 1


if __name__ == "__main__":
    sys.exit(main())