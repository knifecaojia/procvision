#!/usr/bin/env python3
"""
Industrial Vision Application Entry Point

Simple entry point that handles Python path setup and imports
correctly for running the industrial vision application.
"""

import sys
import os
import shutil
from pathlib import Path

# Add current directory to Python path
if getattr(sys, "frozen", False):
    try:
        exe_dir = Path(sys.executable).resolve().parent
        os.chdir(str(exe_dir))
        target_config = exe_dir / "config.json"
        if not target_config.exists():
            candidates = [
                exe_dir / "_internal" / "config.json",
                exe_dir / "_internal" / "config" / "config.json",
            ]
            for src in candidates:
                if src.exists():
                    shutil.copy2(src, target_config)
                    break
    except Exception:
        pass

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Setup environment
os.environ.setdefault('PYTHONPATH', str(current_dir))

try:
    # Import and run the application
    from src.core.app import main

    if __name__ == "__main__":
        print("Starting Industrial Vision Application...")
        print("=" * 50)

        # Check if default user exists
        try:
            from src.auth.services import AuthService
            auth_service = AuthService()
            admin_user = auth_service.get_user_by_username("admin")

            if admin_user:
                print("✓ Default user 'admin' exists")
                print("  You can log in with username 'admin' and password 'admin123'")
            else:
                print("! Default user not found")
                print("  Run: python scripts/create_default_user.py")
                print("  to create the default user")
        except Exception as e:
            print(f"Warning: Could not check default user: {e}")

        print("=" * 50)

        # Run the application
        exit_code = main()
        sys.exit(exit_code)

except ImportError as e:
    print(f"Import error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you're in the project root directory")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Create default user: python scripts/create_default_user.py")
    sys.exit(1)

except Exception as e:
    print(f"Fatal error: {e}")
    sys.exit(1)
