# Specification Delta: Camera Parameter Control System

## ADDED Requirements

### Requirement: SliderField Widget Component
The system SHALL provide a SliderField widget component in `src/ui/components/slider_field.py` for interactive parameter controls.

#### Scenario: SliderField creation with range
- **GIVEN** min=100, max=10000, step=100, decimals=0
- **WHEN** creating `SliderField(100, 10000, 100, 0)`
- **THEN** widget displays correctly with horizontal slider and spin box
- **AND** slider range is 100 to 10000
- **AND** step size is 100

#### Scenario: Value synchronization between slider and spinbox
- **GIVEN** SliderField with value=5000
- **WHEN** user drags slider to 7500
- **THEN** spin box updates to 7500
- **AND** `value_changed` signal emits 7500

#### Scenario: Spinbox updates slider
- **GIVEN** SliderField with value=5000
- **WHEN** user types 8000 in spinbox
- **THEN** slider position updates to 8000
- **AND** `value_changed` signal emits 8000

#### Scenario: Step enforcement on slider drag
- **GIVEN** SliderField with step=100
- **WHEN** user drags slider between 5000 and 5100
- **THEN** value snaps to nearest multiple of 100
- **AND** intermediate values are not emitted

#### Scenario: Decimal precision support
- **GIVEN** SliderField(0, 10, 0.1, 1) for gain parameter
- **WHEN** user adjusts slider
- **THEN** spin box displays values with 1 decimal place
- **AND** values increment by 0.1

### Requirement: Parameter Metadata Schema
The system SHALL define parameter specifications in `src/ui/parameter_schema.py` with complete metadata.

#### Scenario: Parameter metadata accessible
- **GIVEN** parameter_schema module loaded
- **WHEN** accessing metadata for "ExposureTime"
- **THEN** returns dict with keys: min, max, step, unit, display_name
- **AND** min=100, max=100000, step=100, unit="μs"

#### Scenario: All basic parameters defined
- **GIVEN** parameter_schema module
- **WHEN** iterating BASIC_PARAMETERS
- **THEN** includes ExposureTime, Gain, AcquisitionFrameRate
- **AND** each has complete metadata

#### Scenario: Color camera parameters defined
- **GIVEN** parameter_schema module
- **WHEN** accessing COLOR_PARAMETERS
- **THEN** includes WhiteBalance, Saturation, Hue
- **AND** each has appropriate range and unit

#### Scenario: Parameter units displayed correctly
- **GIVEN** parameter with unit="μs"
- **WHEN** creating label for parameter
- **THEN** label text is "曝光时间 (μs)"

### Requirement: Parameter Control Panel Construction
The CameraPage SHALL construct parameter panel with SliderField widgets for each supported parameter.

#### Scenario: Parameter panel renders all controls
- **GIVEN** CameraPage initialized and camera connected
- **WHEN** viewing parameter panel
- **THEN** sees SliderField for ExposureTime
- **AND** sees SliderField for Gain
- **AND** sees SliderField for AcquisitionFrameRate
- **AND** sliders show correct min/max ranges from schema

#### Scenario: Sliders initialize from camera
- **GIVEN** camera connected with ExposureTime=5000
- **WHEN** CameraPage loads parameters
- **THEN** exposure slider positioned at 5000
- **AND** exposure spinbox displays 5000
- **AND** no value_changed signal emitted during initialization

#### Scenario: Parameter groups organized visually
- **GIVEN** parameter panel with multiple parameters
- **WHEN** viewing panel layout
- **THEN** parameters grouped by category (Basic, Image Processing, Color)
- **AND** each group has visual separator
- **AND** group labels displayed

#### Scenario: Read-only parameters disabled
- **GIVEN** parameter marked as read_only in schema
- **WHEN** constructing panel
- **THEN** SliderField is disabled
- **AND** spinbox is disabled
- **AND** tooltip explains "只读参数"

### Requirement: Parameter Value Validation
The system SHALL validate parameter values before applying to camera.

#### Scenario: Out of range value rejected
- **GIVEN** ExposureTime slider range [100, 10000]
- **WHEN** attempting to set value=50000 programmatically
- **THEN** slider clamps value to 10000
- **AND** shows error message: "值必须在 100 到 10000 之间"

#### Scenario: Step mismatch rounded
- **GIVEN** ExposureTime step=100
- **WHEN** entering value=555 in spinbox
- **THEN** value rounded to 600 (nearest step)
- **AND** spinbox updates to 600

#### Scenario: Type validation for float parameters
- **GIVEN** Gain parameter expecting float
- **WHEN** user enters "abc" in spinbox
- **THEN** input rejected
- **AND** spinbox reverts to previous value

### Requirement: Real-time Parameter Application
The CameraPage SHALL apply parameter changes to camera in real-time as user adjusts controls.

#### Scenario: Slider adjustment updates camera
- **GIVEN** camera connected and previewing
- **WHEN** user drags exposure slider from 5000 to 8000
- **THEN** service.set_parameter("ExposureTime", 8000) is called
- **AND** camera parameter updates
- **AND** preview reflects new exposure within 1 second

#### Scenario: Parameter error reverts slider
- **GIVEN** slider at position 5000
- **WHEN** service.set_parameter() returns False
- **THEN** slider reverts to previous value 5000
- **AND** status bar shows error message
- **AND** error logged

#### Scenario: Multiple parameters updated independently
- **GIVEN** camera connected
- **WHEN** user adjusts Gain slider
- **THEN** only Gain parameter updated
- **AND** ExposureTime and other parameters unchanged

### Requirement: Preset Management UI Integration
The CameraPage SHALL provide preset controls for saving, loading, and deleting parameter configurations.

#### Scenario: Preset dropdown populated on connection
- **GIVEN** camera connected with model "MV-CA060-10GM"
- **WHEN** CameraPage loads
- **THEN** preset dropdown populated with saved presets for this model
- **AND** dropdown shows preset names
- **AND** empty if no presets exist

#### Scenario: Save preset workflow
- **GIVEN** camera connected with parameters adjusted
- **WHEN** user clicks "保存预设" button
- **THEN** dialog prompts for preset name
- **WHEN** user enters "Daylight" and confirms
- **THEN** service.save_preset("Daylight", current_user) is called
- **AND** preset appears in dropdown
- **AND** success message shown

#### Scenario: Save preset with duplicate name
- **GIVEN** preset "Daylight" already exists
- **WHEN** user tries to save preset with name "Daylight"
- **THEN** confirmation dialog asks to overwrite
- **WHEN** user confirms
- **THEN** existing preset is overwritten
- **AND** updated preset saved

#### Scenario: Load preset updates all controls
- **GIVEN** preset saved with ExposureTime=8000, Gain=2.0, FPS=30
- **WHEN** user selects preset and clicks "加载预设"
- **THEN** all sliders update to preset values
- **AND** service.set_parameters() called with all preset values
- **AND** camera parameters apply
- **AND** preview updates

#### Scenario: Load preset failure handling
- **GIVEN** preset file corrupted or missing
- **WHEN** attempting to load preset
- **THEN** error dialog shown: "预设加载失败"
- **AND** sliders remain at current values
- **AND** error logged

#### Scenario: Delete preset workflow
- **GIVEN** preset selected in dropdown
- **WHEN** user clicks "删除预设" button
- **THEN** confirmation dialog shown
- **WHEN** user confirms
- **THEN** service.delete_preset() called
- **AND** preset removed from dropdown
- **AND** success message shown

#### Scenario: Preset controls disabled when no camera
- **GIVEN** no camera connected
- **WHEN** viewing preset controls
- **THEN** "保存预设" button disabled
- **AND** "加载预设" button disabled
- **AND** preset dropdown disabled

### Requirement: Parameter Control Styling
The SliderField widgets SHALL match the industrial theme design system.

#### Scenario: SliderField uses industrial colors
- **GIVEN** SliderField widget
- **WHEN** rendered on screen
- **THEN** background is steel grey (#1F232B)
- **AND** slider handle is hover orange (#FF8C32)
- **AND** text is arctic white (#F2F4F8)

#### Scenario: Hover effects on slider
- **GIVEN** SliderField widget
- **WHEN** mouse hovers over slider handle
- **THEN** handle color brightens
- **AND** cursor changes to pointer

#### Scenario: Disabled state styling
- **GIVEN** disabled SliderField
- **WHEN** rendered
- **THEN** slider and spinbox greyed out
- **AND** opacity reduced to 0.5
- **AND** cursor shows not-allowed icon

### Requirement: Image Acquisition API
The CameraService SHALL provide methods for acquiring single frames and image data.

#### Scenario: Get current frame as numpy array
- **GIVEN** camera connected and streaming
- **WHEN** calling `service.get_current_frame()`
- **THEN** returns numpy array with shape (height, width, channels)
- **AND** dtype is uint8
- **AND** array contains latest frame data

#### Scenario: Get frame timeout
- **GIVEN** camera connected but not streaming
- **WHEN** calling `service.get_current_frame(timeout=1.0)`
- **THEN** waits up to 1 second for frame
- **AND** returns None if no frame available
- **AND** logs warning

#### Scenario: Save frame to file
- **GIVEN** camera streaming with current frame
- **WHEN** calling `service.save_frame(filepath, format="png")`
- **THEN** current frame saved to specified path
- **AND** file format is PNG
- **AND** returns True on success

#### Scenario: Get frame metadata
- **GIVEN** camera streaming
- **WHEN** calling `service.get_frame_metadata()`
- **THEN** returns dict with timestamp, frame_id, exposure_time
- **AND** all values are current

## MODIFIED Requirements

None - this is a new parameter control capability.

## REMOVED Requirements

None - no existing parameter control to remove.
