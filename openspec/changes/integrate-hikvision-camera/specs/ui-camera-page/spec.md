# Specification Delta: UI Camera Page Integration

## ADDED Requirements

### Requirement: CameraPage Service Integration
The CameraPage SHALL accept a CameraService instance during initialization and use it for all camera operations.

#### Scenario: CameraPage initializes with service
- **GIVEN** valid CameraService instance
- **WHEN** creating `CameraPage(camera_service)`
- **THEN** page stores service reference
- **AND** service is accessible via `self.camera_service`

#### Scenario: No direct SDK access from UI
- **GIVEN** CameraPage implementation
- **WHEN** searching for CameraManager or Backend usage
- **THEN** found only in `self.camera_service`
- **AND** no direct camera module imports in camera_page.py

### Requirement: Camera Connection Toolbar
The CameraPage SHALL provide toolbar buttons for camera connection management.

#### Scenario: Connect button discovers and connects camera
- **GIVEN** camera connected to system and CameraPage visible
- **WHEN** user clicks "连接相机" button
- **THEN** service.discover_cameras() is called
- **AND** service.connect_camera() is called with first or selected camera
- **AND** status label shows "已连接"
- **AND** camera model name is displayed

#### Scenario: Disconnect button stops preview and disconnects
- **GIVEN** camera connected and previewing
- **WHEN** user clicks "断开连接" button
- **THEN** preview stops if active
- **AND** service.disconnect_camera() is called
- **AND** status label shows "未连接"
- **AND** preview area clears

#### Scenario: Buttons disabled when no camera
- **GIVEN** no camera connected
- **WHEN** viewing CameraPage
- **THEN** "开始预览" button is disabled
- **AND** "停止预览" button is disabled
- **AND** parameter controls are disabled

### Requirement: Live Preview Display
The CameraPage SHALL display live camera preview using PreviewWorker thread.

#### Scenario: Preview starts on button click
- **GIVEN** camera connected and user clicks "开始预览"
- **WHEN** PreviewWorker starts
- **THEN** worker continuously gets frames from camera
- **AND** preview QLabel displays frames
- **AND** "停止预览" button becomes enabled

#### Scenario: Preview displays frames correctly
- **GIVEN** PreviewWorker emitting frames
- **WHEN** receiving `frame_ready(QImage)` signal
- **THEN** preview QLabel updates with new image
- **AND** FPS counter updates from frame metadata
- **AND** frame dimensions shown in status

#### Scenario: Preview stops on button click
- **GIVEN** preview running
- **WHEN** user clicks "停止预览"
- **THEN** PreviewWorker.stop() is called
- **AND** worker thread terminates gracefully
- **AND** preview area shows last frame or placeholder

#### Scenario: Preview handles frame timeout
- **GIVEN** preview running but camera not sending frames
- **WHEN** get_frame() timeout occurs
- **THEN** FPS counter shows 0
- **AND** warning logged
- **AND** worker continues attempting to get frames

### Requirement: PreviewWorker Thread Implementation
The CameraPage SHALL use PreviewWorker QThread for frame acquisition.

#### Scenario: PreviewWorker initializes with camera
- **GIVEN** connected CameraDevice instance
- **WHEN** creating `PreviewWorker(camera)`
- **THEN** worker stores camera reference
- **AND** worker is ready to start

#### Scenario: PreviewWorker runs frame loop
- **GIVEN** PreviewWorker started
- **WHEN** worker.run() executes
- **THEN** continuously calls camera.get_frame()
- **AND** emits `frame_ready(QImage)` signal for each frame
- **AND** emits `stats_updated(dict)` signal with FPS/timestamp

#### Scenario: PreviewWorker stops gracefully
- **GIVEN** running PreviewWorker
- **WHEN** worker.stop() is called
- **THEN** worker sets stop flag
- **AND** run loop exits
- **AND** thread terminates within 1 second

### Requirement: Camera Status Panel
The CameraPage SHALL display real-time camera status information.

#### Scenario: Status panel shows connection state
- **GIVEN** camera just connected
- **WHEN** connection completes
- **THEN** model label shows camera model name
- **AND** status label shows "已连接 | 就绪"
- **AND** serial number displayed (if available)

#### Scenario: Status panel shows FPS
- **GIVEN** preview running
- **WHEN** receiving frames
- **THEN** FPS label updates every second
- **AND** displays actual frame rate (e.g., "30.5 FPS")

#### Scenario: Status panel shows temperature
- **GIVEN** camera supports temperature reporting
- **WHEN** temperature data available
- **THEN** temperature label shows current value
- **AND** format is "温度: 45°C"

#### Scenario: Status panel clears on disconnect
- **GIVEN** camera connected with status displayed
- **WHEN** disconnecting camera
- **THEN** all status labels reset to default
- **AND** model shows "未连接"

### Requirement: Screenshot Capture
The CameraPage SHALL provide screenshot capture functionality.

#### Scenario: Screenshot saves current frame
- **GIVEN** preview running with live frames
- **WHEN** user clicks "截图" button
- **THEN** current frame is saved to file
- **AND** file saved to `data/screenshots/{timestamp}.png`
- **AND** success message shown with file path

#### Scenario: Screenshot disabled when no preview
- **GIVEN** camera connected but preview stopped
- **WHEN** viewing toolbar
- **THEN** "截图" button is disabled

### Requirement: Error Handling in UI
The CameraPage SHALL handle camera errors gracefully with user-friendly messages.

#### Scenario: Connection failure shows error dialog
- **GIVEN** attempting to connect to unavailable camera
- **WHEN** service.connect_camera() returns False
- **THEN** QMessageBox displays error: "连接失败，请检查相机连接"
- **AND** status shows "未连接"

#### Scenario: Preview failure shows status message
- **GIVEN** attempting to start preview
- **WHEN** service.start_preview() returns False
- **THEN** status bar shows: "预览启动失败"
- **AND** preview worker is not started

#### Scenario: SDK not found shows warning
- **GIVEN** Hikvision MVS SDK not installed
- **WHEN** CameraPage loads
- **THEN** status label shows "SDK未安装"
- **AND** all camera controls disabled
- **AND** help text displayed with installation instructions

## MODIFIED Requirements

None - CameraPage is being enhanced with new camera integration features, not modifying existing behavior.

## REMOVED Requirements

None - existing CameraPage placeholder functionality is being replaced, not removed.
