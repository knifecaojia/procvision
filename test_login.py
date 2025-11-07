#!/usr/bin/env python3
"""
Quick test script for login functionality.
"""

import sys
from pathlib import Path

# Add src directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from src.auth.services import AuthService
    from src.utils.validators import InputValidator

    def test_validation():
        """Test username validation."""
        print("Testing username validation...")

        # Test admin username (should work now)
        is_valid, error = InputValidator.validate_username("admin")
        print(f"  Username 'admin': {is_valid}, Error: {error}")

        # Test other reserved usernames (should fail)
        reserved_usernames = ['administrator', 'root', 'system']
        for username in reserved_usernames:
            is_valid, error = InputValidator.validate_username(username)
            print(f"  Username '{username}': {is_valid}, Error: {error}")

        print()

    def test_auth_service():
        """Test authentication service."""
        print("Testing authentication service...")

        auth_service = AuthService()

        # Test user lookup
        user_data = auth_service.get_user_by_username("admin")
        if user_data:
            print(f"  Found user 'admin': ID={user_data['id']}, Active={user_data['is_active']}")
        else:
            print("  User 'admin' not found")

        print()

    if __name__ == "__main__":
        print("Quick Login System Test")
        print("=" * 40)

        test_validation()
        test_auth_service()

        print("Test completed!")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)