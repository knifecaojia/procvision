#!/usr/bin/env python
"""
Verification script for camera integration fixes.
Tests that all components are properly integrated without requiring hardware.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all camera modules can be imported."""
    print("Testing imports...")

    try:
        from src.camera import CameraService, PresetManager, CameraManager
        print("  ✓ Camera modules import successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_config():
    """Test that camera config exists."""
    print("\nTesting configuration...")

    try:
        from src.core.config import get_config
        config = get_config()

        if hasattr(config, 'camera'):
            print("  ✓ CameraConfig exists in AppConfig")
            print(f"    - SDK path: {config.camera.sdk_path or 'Not set'}")
            print(f"    - Preview enabled: {config.camera.enable_preview}")
            print(f"    - Preview FPS limit: {config.camera.preview_fps_limit}")
            return True
        else:
            print("  ✗ CameraConfig not found in AppConfig")
            return False

    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        return False

def test_ui_components():
    """Test that UI components exist."""
    print("\nTesting UI components...")

    try:
        from src.ui.components import SliderField, PreviewWorker
        print("  ✓ SliderField and PreviewWorker available")
        return True
    except ImportError as e:
        print(f"  ✗ UI component import failed: {e}")
        return False

def test_camera_page():
    """Test that CameraPage has correct signature."""
    print("\nTesting CameraPage...")

    try:
        from src.ui.pages.camera_page import CameraPage
        import inspect

        sig = inspect.signature(CameraPage.__init__)
        params = list(sig.parameters.keys())

        if 'camera_service' in params:
            print("  ✓ CameraPage.__init__ has camera_service parameter")
            print(f"    Parameters: {', '.join(params)}")
            return True
        else:
            print("  ✗ CameraPage.__init__ missing camera_service parameter")
            print(f"    Current parameters: {', '.join(params)}")
            return False

    except Exception as e:
        print(f"  ✗ CameraPage test failed: {e}")
        return False

def test_app_integration():
    """Test that app initializes camera service."""
    print("\nTesting app integration...")

    try:
        # Read app.py to check for camera service
        app_file = Path(__file__).parent / "src" / "core" / "app.py"
        content = app_file.read_text(encoding='utf-8')

        checks = {
            'Import CameraService': 'from ..camera import CameraService' in content or 'from src.camera import CameraService' in content,
            'Initialize camera_service': 'self.camera_service = CameraService' in content,
            'Cleanup camera_service': "hasattr(self, 'camera_service')" in content and 'self.camera_service.stop_preview()' in content,
            'Pass app to MainWindow': 'MainWindow(self.session_manager, self)' in content,
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"  ✗ App integration test failed: {e}")
        return False

def test_main_window_integration():
    """Test that MainWindow accepts app parameter."""
    print("\nTesting MainWindow integration...")

    try:
        # Read main_window.py to check for app parameter
        main_window_file = Path(__file__).parent / "src" / "ui" / "main_window.py"
        content = main_window_file.read_text(encoding='utf-8')

        checks = {
            'Accept app parameter': 'def __init__(self, session_manager: SessionManager, app=' in content,
            'Store app reference': 'self.app = app' in content,
            'Pass camera_service to CameraPage': 'CameraPage(camera_service=' in content,
        }

        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"  ✗ MainWindow integration test failed: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist."""
    print("\nTesting directory structure...")

    data_dir = Path(__file__).parent / "data" / "camera_presets"

    if data_dir.exists():
        print(f"  ✓ camera_presets directory exists: {data_dir}")
        return True
    else:
        print(f"  ✗ camera_presets directory not found: {data_dir}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Camera Integration Verification")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("UI Components", test_ui_components),
        ("CameraPage", test_camera_page),
        ("App Integration", test_app_integration),
        ("MainWindow Integration", test_main_window_integration),
        ("Directory Structure", test_directory_structure),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! Camera integration is correctly configured.")
        print("\nNext steps:")
        print("1. Install Hikvision MVS SDK if not already installed")
        print("2. Connect a Hikvision camera")
        print("3. Run the application: python -m src.core.app")
        print("4. Test camera connection and preview features")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
