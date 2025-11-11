# Specification Delta: Camera Integration Backend System

## ADDED Requirements

### Requirement: SDK Module Structure
The system SHALL provide camera SDK modules in `src/camera/` directory with all necessary components for Hikvision MVS SDK integration.

#### Scenario: SDK modules are importable
- **GIVEN** all SDK modules are in place
- **WHEN** importing from `src.camera`
- **THEN** all imports succeed without ImportError
- **AND** CameraManager, CameraDevice, CameraInfo classes are available

#### Scenario: Abstract base classes enforce implementation
- **GIVEN** CameraBackend is an abstract class
- **WHEN** attempting to instantiate it directly
- **THEN** TypeError is raised with message about abstract methods

#### Scenario: Hikvision backend loads with SDK
- **GIVEN** Hikvision MVS SDK is installed and MVCAM_COMMON_RUNENV is set
- **WHEN** importing HikvisionBackend
- **THEN** import succeeds and class is available

#### Scenario: SDK fails gracefully without MVS
- **GIVEN** Hikvision MVS SDK is not installed
- **WHEN** importing HikvisionBackend
- **THEN** ImportError is raised with clear message about missing SDK

### Requirement: CameraService API
The system SHALL provide CameraService class in `src/camera/camera_service.py` to encapsulate all camera operations.

#### Scenario: Service initialization
- **GIVEN** valid CameraConfig with SDK path
- **WHEN** creating CameraService(config)
- **THEN** service initializes successfully
- **AND** current_camera is None
- **AND** manager is initialized

#### Scenario: Discover cameras
- **GIVEN** service is initialized and cameras are connected
- **WHEN** calling service.discover_cameras()
- **THEN** returns list of CameraInfo objects
- **AND** each has id, name, model, transport

#### Scenario: Connect to camera
- **GIVEN** discovered camera with CameraInfo
- **WHEN** calling service.connect_camera(camera_info)
- **THEN** returns True
- **AND** get_connected_camera() returns CameraDevice

#### Scenario: Disconnect camera
- **GIVEN** connected camera
- **WHEN** calling service.disconnect_camera()
- **THEN** camera is disconnected
- **AND** get_connected_camera() returns None

#### Scenario: Get all parameters
- **GIVEN** connected camera
- **WHEN** calling service.get_all_parameters()
- **THEN** returns dictionary of {key: value}
- **AND** includes ExposureTime, Gain, AcquisitionFrameRate

#### Scenario: Set parameter
- **GIVEN** connected camera with ExposureTime=5000
- **WHEN** calling service.set_parameter("ExposureTime", 10000)
- **THEN** returns True
- **AND** camera parameter is updated to 10000

#### Scenario: Set parameters batch
- **GIVEN** connected camera
- **WHEN** calling service.set_parameters({"ExposureTime": 5000, "Gain": 1.5})
- **THEN** returns dict with each parameter's success status

#### Scenario: Start and stop preview
- **GIVEN** connected camera
- **WHEN** calling service.start_preview()
- **THEN** returns True
- **AND** camera streaming is active
- **WHEN** calling service.is_streaming()
- **THEN** returns True
- **WHEN** calling service.stop_preview()
- **THEN** streaming stops

### Requirement: Preset File Storage
The system SHALL provide PresetManager class in `src/camera/preset_manager.py` for JSON-based preset storage.

#### Scenario: Save preset creates file
- **GIVEN** valid parameters, user="admin", camera="MV-CA060", name="Daylight"
- **WHEN** calling save_preset("Daylight", "admin", "MV-CA060", {"exposure": 5000})
- **THEN** file created at `data/camera_presets/admin/Daylight.json`
- **AND** file contains correct JSON with parameters

#### Scenario: Load preset reads file
- **GIVEN** existing preset file for user "admin" and camera "MV-CA060"
- **WHEN** calling load_preset("Daylight", "MV-CA060", "admin")
- **THEN** returns dictionary with parameters

#### Scenario: List presets filters by user and camera
- **GIVEN** multiple presets for different users and cameras
- **WHEN** calling list_presets("MV-CA060", "admin")
- **THEN** returns only presets for admin user and MV-CA060 camera

#### Scenario: Delete preset removes file
- **GIVEN** existing preset file
- **WHEN** calling delete_preset("Daylight", "MV-CA060", "admin")
- **THEN** file is removed from filesystem
- **AND** subsequent load returns None

#### Scenario: Ensure directory creates missing paths
- **GIVEN** directory `data/camera_presets/admin/` doesn't exist
- **WHEN** calling ensure_directory()
- **THEN** all necessary directories are created

### Requirement: Thread Safety
The camera backend SHALL provide thread-safe parameter access using RLock.

#### Scenario: Concurrent parameter access
- **GIVEN** camera connected and streaming
- **WHEN** multiple threads call get_parameter() simultaneously
- **THEN** all calls complete without error
- **AND** values are consistent

#### Scenario: Parameter set during streaming
- **GIVEN** preview worker reading frames
- **WHEN** UI thread sets ExposureTime parameter
- **THEN** parameter update completes without blocking frame acquisition
- **AND** new value takes effect within 1 second

### Requirement: Camera Lifecycle Management
The system SHALL manage camera connection lifecycle with proper resource cleanup.

#### Scenario: Camera connects successfully
- **GIVEN** camera discovered with valid CameraInfo
- **WHEN** calling connect_camera()
- **THEN** camera handle is opened
- **AND** device is initialized
- **AND** parameters are readable

#### Scenario: Camera disconnects cleanly
- **GIVEN** camera connected and streaming
- **WHEN** calling disconnect_camera()
- **THEN** streaming stops
- **AND** camera handle is closed
- **AND** resources are freed

#### Scenario: Double disconnect is safe
- **GIVEN** camera already disconnected
- **WHEN** calling disconnect_camera() again
- **THEN** no error raised
- **AND** operation completes immediately

### Requirement: Error Handling
The camera system SHALL handle errors gracefully with appropriate logging.

#### Scenario: Connection failure is logged
- **GIVEN** attempting to connect to unavailable camera
- **WHEN** connect_camera() fails
- **THEN** error is logged with details
- **AND** returns False
- **AND** no exception raised

#### Scenario: Parameter out of range
- **GIVEN** connected camera
- **WHEN** setting ExposureTime to invalid value
- **THEN** error is logged
- **AND** returns False
- **AND** camera parameter unchanged

#### Scenario: Frame timeout handled
- **GIVEN** camera streaming but not sending frames
- **WHEN** get_frame() times out
- **THEN** warning is logged
- **AND** returns None
- **AND** camera remains connected

### Requirement: Logging Integration
The camera system SHALL integrate with application logging system.

#### Scenario: SDK discovery logs correctly
- **GIVEN** logging configured at INFO level
- **WHEN** discovering cameras
- **THEN** log shows: "Discovered N cameras from Hikvision backend"

#### Scenario: Service parameter set logs
- **GIVEN** logging configured at DEBUG level
- **WHEN** setting parameter via service
- **THEN** log shows: "Setting parameter ExposureTime to 5000"

#### Scenario: Preset save logs at INFO
- **GIVEN** INFO level logging
- **WHEN** saving preset
- **THEN** log shows: "Saved preset 'Daylight' for user admin"

## MODIFIED Requirements

### Requirement: Application Configuration
The AppConfig in `src/core/config.py` SHALL be extended to include camera configuration.

#### Scenario: Configuration loads with camera settings
- **GIVEN** config file with camera section
- **WHEN** calling get_config()
- **THEN** returned config includes camera attribute
- **AND** camera settings have default or configured values

#### Scenario: Environment variable overrides SDK path
- **GIVEN** environment variable SMART_VISION_CAMERA_SDK_PATH=/opt/mvs
- **WHEN** loading configuration
- **THEN** config.camera.sdk_path equals /opt/mvs

#### Scenario: Configuration ensures directories
- **GIVEN** config with camera settings
- **WHEN** configuration loads
- **THEN** `data/camera_presets/` directory is created if not exists
