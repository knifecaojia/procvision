# Proposal: Integrate Hikvision Industrial Camera Support

## Why

The SMART-VISION industrial vision system currently lacks real camera hardware integration. Users need the ability to connect to Hikvision industrial cameras, view live preview, adjust camera parameters in real-time, and manage parameter presets for different inspection scenarios. A working reference implementation exists in `F:/Ai-LLM/southwest/04hkvision-cam-poc` that demonstrates successful integration with the Hikvision MVS SDK.

## What Changes

- Add camera SDK modules (`src/camera/`) with Hikvision MVS SDK integration
- Create `CameraService` API layer to encapsulate all camera operations
- Implement `PresetManager` for JSON file-based parameter preset storage
- Add `SliderField` widget component for interactive parameter controls
- Integrate live camera preview in `CameraPage` using `PreviewWorker` thread
- Add parameter control panel with sliders for exposure, gain, FPS, and other camera settings
- Implement preset save/load/delete functionality with per-user storage
- Add camera status monitoring (connection state, FPS, temperature)
- Update `AppConfig` to include `CameraConfig` with SDK path and preview settings
- Add logging integration for camera operations (`camera.sdk`, `camera.service`, `camera.preset`)

**BREAKING**: Requires Hikvision MVS SDK installation on target system. No mock fallback provided - this is for real hardware only.

## Impact

**Affected Specs:**
- `camera-integration` (NEW) - Backend SDK integration and service layer
- `ui-camera-page` (MODIFIED) - Camera page UI integration with live preview
- `camera-parameter-control` (NEW) - Parameter control widgets and preset management

**Affected Code:**
- `src/camera/` (NEW) - Entire camera SDK module
- `src/ui/pages/camera_page.py` (MODIFIED) - Integrate with CameraService
- `src/ui/components/slider_field.py` (NEW) - Parameter control widget
- `src/core/config.py` (MODIFIED) - Add CameraConfig dataclass
- `src/core/app.py` (MODIFIED) - Initialize and manage CameraService lifecycle
- `requirements.txt` (MODIFIED) - Add numpy dependency

**Data Files:**
- `data/camera_presets/{username}/{preset_name}.json` - Per-user preset storage

**Dependencies:**
- External: Hikvision MVS SDK (system-level installation required)
- Python: numpy>=1.21.0

**Testing Requirements:**
- Requires at least one Hikvision GigE or USB camera for integration testing
- No automated testing without real hardware
