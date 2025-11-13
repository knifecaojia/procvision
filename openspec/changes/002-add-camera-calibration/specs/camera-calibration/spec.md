# Camera Calibration Feature Specification

## Purpose
Add camera intrinsic calibration using OpenCV chessboard detection to the camera page, allowing users to capture calibration images, detect corners, compute camera matrix and distortion coefficients, and save results as JSON.

## ADDED Requirements

### Requirement: Add calibration button to camera page

**The system SHALL provide a calibration button in the camera preview toolbar.**

#### Scenario: Display calibration button when camera connected

**GIVEN** the user has connected to a camera
**WHEN** viewing the camera page preview controls
**THEN** a calibration button shall be visible in the toolbar
**AND** the button shall display a ruler icon or "标" text
**AND** the button shall be in enabled state

#### Scenario: Disable calibration button when camera disconnected

**GIVEN** no camera is connected to the system
**WHEN** viewing the camera page preview controls
**THEN** the calibration button shall be disabled
**AND** the button tooltip shall indicate camera must be connected first

#### Scenario: Click calibration button to open dialog

**GIVEN** a camera is connected and previewing
**WHEN** the user clicks the calibration button
**THEN** the system shall open CameraCalibrationDialog as a modal
**AND** the dialog shall display real-time camera preview
**AND** the dialog shall show chessboard configuration controls
**AND** the dialog shall display an empty image gallery

### Requirement: Implement calibration data model

**The system SHALL define data structures for calibration workflow.**

#### Scenario: Create CalibrationImage object

**GIVEN** a captured camera frame as numpy array
**AND** detected chessboard corners coordinates
**WHEN** creating a CalibrationImage dataclass instance
**THEN** the object shall store timestamp, image data, corners, and board size

#### Scenario: Create CalibrationResult with camera parameters

**GIVEN** computed camera matrix K (3x3)
**AND** distortion coefficients array (5 or 8 elements)
**AND** reprojection error value
**WHEN** creating a CalibrationResult dataclass instance
**THEN** the object shall store camera_matrix, distortion_coeffs, reprojection_error
**AND** metadata including timestamp, board_size, square_size_mm, image_resolution

#### Scenario: Validate ChessboardConfig parameters

**GIVEN** user specifies rows=9, cols=6, square_size_mm=25.0
**WHEN** creating a ChessboardConfig dataclass instance
**THEN** the object shall validate rows between 4-20
**AND** cols between 4-20
**AND** square_size_mm between 1.0-200.0

### Requirement: Detect chessboard corners using OpenCV

**The system SHALL use OpenCV to detect chessboard corners in images.**

#### Scenario: Detect corners in grayscale image

**GIVEN** a grayscale image containing a chessboard pattern
**AND** board size is 9 rows and 6 columns
**WHEN** calling cv2.findChessboardCorners()
**THEN** the function shall return success=True if pattern found
**AND** return corner coordinates in format (N, 1, 2)

#### Scenario: Refine corners to sub-pixel precision

**GIVEN** initially detected corners at pixel level
**WHEN** calling cv2.cornerSubPix() with termination criteria (30 iterations, 0.001 epsilon)
**THEN** corner coordinates shall be refined to sub-pixel accuracy

### Requirement: Implement calibration service

**The system SHALL provide CalibrationService to manage calibration workflow.**

#### Scenario: Capture image when chessboard visible

**GIVEN** camera is streaming
**AND** chessboard is positioned in camera view
**WHEN** calling capture_calibration_image(board_size=(9, 6))
**THEN** the service shall capture current frame
**AND** convert to grayscale
**AND** detect chessboard corners
**AND** if detected, store CalibrationImage object
**AND** return True

#### Scenario: Capture fails without chessboard

**GIVEN** camera is streaming
**AND** no chessboard in view
**WHEN** calling capture_calibration_image()
**THEN** corner detection shall fail
**AND** the service shall return False
**AND** no image shall be stored

#### Scenario: Execute calibration calculation

**GIVEN** 15 valid calibration images stored
**AND** all have detected corners
**WHEN** calling calibrate(board_size=(9, 6), square_size_mm=25.0)
**THEN** the service shall collect all object_points and image_points
**AND** call cv2.calibrateCamera()
**AND** return CalibrationResult with camera_matrix and distortion_coeffs
**AND** calculate reprojection error

#### Scenario: Check calibration progress

**GIVEN** 8 images have been captured
**AND** minimum required is 15
**WHEN** calling get_progress()
**THEN** the service shall return (8, 15)

#### Scenario: Reset calibration data

**GIVEN** calibration service has 10 images stored
**WHEN** calling reset()
**THEN** all stored images shall be cleared
**AND** progress shall return to (0, 15)

### Requirement: Handle calibration errors

**The system SHALL handle errors gracefully with user-friendly messages.**

#### Scenario: Camera not connected during capture

**GIVEN** camera service is not connected
**WHEN** calling capture_calibration_image()
**THEN** the service shall detect no frame available
**AND** raise CameraNotConnectedException
**AND** log error with camera status

#### Scenario: Insufficient images for calibration

**GIVEN** only 10 valid images stored
**WHEN** calling calibrate()
**THEN** the service shall check image count
**AND** raise InsufficientImagesException requiring 15 images
**AND** log warning with current count

#### Scenario: Calibration calculation fails

**GIVEN** valid images but OpenCV calibration fails
**WHEN** calling calibrate()
**THEN** the service shall catch cv2.calibrateCamera() exception
**AND** raise CalibrationFailedException with error details
**AND** log error with failure reason

### Requirement: Load configuration for calibration

**The system SHALL load calibration parameters from configuration.**

#### cfg: Load minimum images from config

**GIVEN** config.json contains calibration.min_images=20
**WHEN** creating CalibrationService
**THEN** the service shall use 20 as minimum required images

#### Scenario: Load default board size from config

**GIVEN** config.json contains calibration.default_board_rows=7 and default_board_cols=5
**WHEN** opening calibration dialog
**THEN** the rows spinbox shall default to 7
**AND** the cols spinbox shall default to 5

### Requirement: Log calibration activities

**The system SHALL log calibration workflow activities.**

#### Scenario: Log successful image capture

**GIVEN** capture_calibration_image() succeeds
**WHEN** the function returns
**THEN** an INFO log entry shall be written with timestamp and image count

#### Scenario: Log calibration completion

**GIVEN** calibrate() completes successfully
**WHEN** the function returns CalibrationResult
**THEN** an INFO log entry shall be written with reprojection error
**AND** camera matrix parameters shall be logged at DEBUG level

### Requirement: Persist results to JSON

**The system SHALL save calibration results as JSON files.**

#### Scenario: Save calibration JSON with numpy arrays

**GIVEN** CalibrationResult with camera_matrix (3x3 numpy array)
**AND** distortion_coeffs (5 element numpy array)
**WHEN** calling save_calibration_result(result, camera_model)
**THEN** the camera_matrix shall be converted to nested list format
**AND** distortion_coeffs shall be converted to list format
**AND** JSON file shall contain arrays as lists

#### scenario: Load calibration JSON reconstruct numpy arrays

**GIVEN** a JSON file with nested lists for camera_matrix
**WHEN** calling load_calibration_result(file_path)
**THEN** the lists shall be converted back to numpy arrays
**AND** the returned CalibrationResult shall have proper numpy types

#### Scenario: Create storage directory automatically

**GIVEN** storage path does not exist
**WHEN** calling save_calibration_result()
**THEN** all parent directories shall be created automatically
**AND** PermissionError shall be caught and converted to PermissionDeniedException

### Requirement: Manage calibration history

**The system SHALL maintain calibration history with automatic cleanup.**

#### Scenario: List all calibration files

**GIVEN** 5 calibration JSON files exist for camera model
**WHEN** calling list_calibration_files(camera_model)
**THEN** a list of 5 file paths shall be returned
**AND** files shall be sorted by timestamp descending (newest first)

#### Scenario: Enforce max calibration files limit

**GIVEN** 35 calibration files exist (limit is 30)
**WHEN** saving a new calibration file
**THEN** the 5 oldest files shall be deleted
**AND** the directory shall contain exactly 30 files

#### scenario: Load most recent calibration

**GIVEN** multiple calibration files exist for camera model
**WHEN** calling load_latest_calibration(camera_model)
**THEN** the function shall list all calibration files
**AND** load and return the most recent CalibrationResult
try
