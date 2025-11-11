# Tasks: Hikvision Camera Integration Implementation

## Phase 1: SDK Foundation (2-3 hours)

### Task 1.1: Copy SDK Modules from Reference Project
**Duration:** 1 hour
**Dependencies:** None
**Description:** Copy camera SDK modules from reference project.

**Steps:**
1. Create `src/camera/` directory
2. Copy files from `F:/Ai-LLM/southwest/04hkvision-cam-poc/sdk/`:
   - backend.py
   - camera_device.py
   - camera_manager.py
   - types.py
   - exceptions.py
   - hikvision_backend.py
3. Create `__init__.py` with necessary exports
4. Update import statements to use `src.camera` package

**Deliverables:**
- `src/camera/__init__.py`
- `src/camera/backend.py`
- `src/camera/camera_device.py`
- `src/camera/camera_manager.py`
- `src/camera/types.py`
- `src/camera/exceptions.py`
- `src/camera/hikvision_backend.py`

**Verification:**
```bash
python -c "from src.camera import CameraManager, CameraDevice; print('OK')"
```

### Task 1.2: Create CameraService
**Duration:** 1 hour
**Dependencies:** Task 1.1
**Description:** Implement service layer API.

**Steps:**
1. Create `src/camera/camera_service.py`
2. Implement constructor with CameraManager and PresetManager
3. Add lifecycle methods (discover, connect, disconnect)
4. Add parameter methods (get_all, set, get_range)
5. Add stream methods (start/stop preview, is_streaming)
6. Add logging for all operations

**Deliverables:**
- `src/camera/camera_service.py`

**Verification:**
```python
from src.camera import CameraService
from src.core.config import get_config

service = CameraService(get_config().camera)
cameras = service.discover_cameras()
print(f"Found {len(cameras)} cameras")
```

### Task 1.3: Create PresetManager
**Duration:** 30 minutes
**Dependencies:** Task 1.2
**Description:** Implement preset file operations.

**Steps:**
1. Create `src/camera/preset_manager.py`
2. Implement save_preset() - write JSON to `data/camera_presets/{user}/{name}.json`
3. Implement load_preset() - read and parse JSON
4. Implement list_presets() - scan directory, filter by camera model
5. Implement delete_preset() - delete file
6. Ensure directory exists

**Deliverables:**
- `src/camera/preset_manager.py`
- `data/camera_presets/` directory

**Verification:**
```python
from src.camera import PresetManager

pm = PresetManager()
pm.save_preset("test", "admin", "MV-CA060", {"exposure": 5000})
```

### Task 1.4: Update Configuration
**Duration:** 30 minutes
**Dependencies:** Task 1.2
**Description:** Add camera configuration to config system.

**Steps:**
1. Open `src/core/config.py`
2. Add `CameraConfig` dataclass:
   ```python
   @dataclass
   class CameraConfig:
       sdk_path: Optional[str] = None
       enable_preview: bool = True
       preview_fps_limit: int = 30
       auto_connect: bool = False
   ```
3. Add to `AppConfig`:
   ```python
   camera: CameraConfig = field(default_factory=CameraConfig)
   ```
4. Add environment variable mapping: `SMART_VISION_CAMERA_SDK_PATH`
5. Create directories: `data/camera_presets/`

**Deliverables:**
- Modified `src/core/config.py`
- Directory structure created

**Verification:**
```python
from src.core.config import get_config
config = get_config()
print(config.camera.sdk_path)
```

### Task 1.5: Update Requirements
**Duration:** 15 minutes
**Dependencies:** None
**Description:** Add numpy dependency.

**Steps:**
1. Open `requirements.txt`
2. Add `numpy>=1.21.0`
3. Install: `pip install -r requirements.txt`

**Verification:**
```bash
python -c "import numpy; print(numpy.__version__)"
```

**End of Phase 1**: All backend infrastructure ready

## Phase 2: UI Components (2-3 hours)

### Task 2.1: Create SliderField Widget
**Duration:** 1 hour
**Dependencies:** Phase 1 complete
**Description:** Copy and adapt SliderField from reference project.

**Steps:**
1. Copy `SliderField` from `04hkvision-cam-poc/ui/main_window.py`
2. Create `src/ui/components/slider_field.py`
3. Adapt to industrial theme (colors, fonts)
4. Test widget in isolation

**Deliverables:**
- `src/ui/components/slider_field.py`
- `src/ui/components/__init__.py` (if needed)

**Verification:**
```python
from src.ui.components.slider_field import SliderField
from PySide6.QtWidgets import QApplication

app = QApplication()
slider = SliderField(100, 10000, 100, 0)
slider.show()
app.exec()
```

### Task 2.2: Create PreviewWorker
**Duration:** 1 hour
**Dependencies:** Task 2.1
**Description:** Create QThread worker for frame acquisition.

**Steps:**
1. Create `src/ui/components/preview_worker.py`
2. Implement QThread subclass
3. Loop calling `camera.get_frame()`
4. Emit `frame_ready(QImage)` signal
5. Emit `stats_updated(dict)` signal

**Deliverables:**
- `src/ui/components/preview_worker.py`

### Task 2.3: Create Parameter Schema
**Duration:** 30 minutes
**Dependencies:** Phase 1 complete
**Description:** Define parameter metadata for UI.

**Steps:**
1. Create `src/ui/parameter_schema.py`
2. Define common parameters (exposure, gain, fps, gamma)
3. Define color camera parameters (white balance, saturation)
4. Define ranges and step sizes

**Deliverables:**
- `src/ui/parameter_schema.py`

## Phase 3: CameraPage Integration (3-4 hours)

### Task 3.1: Refactor CameraPage Constructor
**Duration:** 30 minutes
**Dependencies:** Phases 1-2 complete
**Description:** Add CameraService to CameraPage.

**Steps:**
1. Open `src/ui/pages/camera_page.py`
2. Modify `__init__` to accept `camera_service: CameraService`
3. Store as `self.camera_service`
4. Initialize preview worker reference
5. Initialize connection state tracking

**Changes:**
```python
class CameraPage(QFrame):
    def __init__(self, camera_service: CameraService, parent=None):
        super().__init__(parent)
        self.camera_service = camera_service
        self.preview_worker = None
        # ...
```

### Task 3.2: Implement Camera Connection
**Duration:** 1 hour
**Dependencies:** Task 3.1
**Description:** Hook up connection controls.

**Steps:**
1. Connect "连接相机" button to `on_connect_camera()`
2. Connect "断开连接" button to `on_disconnect_camera()`
3. Implement `on_connect_camera()`:
   - Call `service.discover_cameras()`
   - Show selection dialog or connect to first
   - Call `service.connect_camera()`
   - Update status panel
4. Implement `on_disconnect_camera()`:
   - Stop preview if active
   - Call `service.disconnect_camera()`
   - Clear UI state

### Task 3.3: Implement Live Preview
**Duration:** 1.5 hours
**Dependencies:** Tasks 2.2, 3.2
**Description:** Integrate preview worker and display.

**Steps:**
1. Replace placeholder QLabel with proper preview widget
2. Connect "开始预览" to `on_start_preview()`
3. Connect "停止预览" to `on_stop_preview()`
4. Implement `on_start_preview()`:
   - Get camera from `service.get_connected_camera()`
   - Create PreviewWorker(camera)
   - Connect `frame_ready` signal to preview label
   - Connect `stats_updated` to FPS update
   - Start worker thread
5. Implement `on_stop_preview()`:
   - Call worker.stop()
   - Nullify worker reference

### Task 3.4: Implement Status Panel
**Duration:** 30 minutes
**Dependencies:** Task 3.2
**Description:** Update status labels dynamically.

**Steps:**
1. Make status labels instance variables:
   - `self.model_label`
   - `self.status_label`
   - `self.fps_label`
   - `self.temp_label`
2. Add method `update_status_panel()`
3. Update on connection change
4. Update FPS from preview worker stats
5. Update temperature (if available from camera)

### Task 3.5: Implement Parameter Controls
**Duration:** 1 hour
**Dependencies:** Tasks 2.1, 3.2
**Description:** Replace static inputs with SliderField.

**Steps:**
1. Remove QLineEdit controls
2. Create SliderField for each parameter:
   - Exposure (100-100000, step 100)
   - Gain (0-10, step 0.1)
   - FPS (1-60, step 1)
3. Initialize sliders from current camera parameters
4. Connect `value_changed` signal to `on_parameter_changed()`
5. Implement `on_parameter_changed()`:
   - Get sender parameter key
   - Call `service.set_parameter(key, value)`
   - Handle errors (show status message, revert slider)

## Phase 4: Preset Management (1.5 hours)

### Task 4.1: Add Preset UI Controls
**Duration:** 30 minutes
**Dependencies:** Phase 3 complete
**Description:** Add preset save/load UI.

**Steps:**
1. Add preset dropdown (QComboBox)
2. Add "保存预设" button
3. Add "加载预设" button
4. Add "删除预设" button

### Task 4.2: Implement Preset Save
**Duration:** 30 minutes
**Dependencies:** Task 4.1
**Description:** Save current parameters to file.

**Steps:**
1. Connect "保存预设" to `on_save_preset()`
2. Show dialog to input preset name
3. Call `service.save_preset(name)`
4. Refresh preset dropdown
5. Show success message

### Task 4.3: Implement Preset Load
**Duration:** 30 minutes
**Dependencies:** Task 4.2
**Description:** Load and apply preset.

**Steps:**
1. Connect "加载预设" to `on_load_preset()`
2. Get selected preset name
3. Call `service.load_preset(name)`
4. Update all sliders to new values
5. Apply parameters to camera

### Task 4.4: Implement Preset Delete
**Duration:** 20 minutes
**Dependencies:** Task 4.1
**Description:** Delete preset file.

**Steps:**
1. Connect "删除预设" to `on_delete_preset()`
2. Get selected preset name
3. Show confirmation dialog
4. Call `service.delete_preset(name)`
5. Refresh dropdown

## Phase 5: Polish & Integration (2 hours)

### Task 5.1: Initialize CameraService in Application
**Duration:** 30 minutes
**Dependencies:** All previous phases
**Description:** Hook camera service into app lifecycle.

**Steps:**
1. Open `src/core/app.py`
2. In `IndustrialVisionApp.__init__()`:
   - Create `CameraService` instance
   - Store as `self.camera_service`
3. Pass service to CameraPage when creating
4. Add cleanup in `cleanup()`:
   - Stop preview
   - Disconnect camera
   - Delete service reference

### Task 5.2: Add Error Handling
**Duration:** 45 minutes
**Dependencies:** All UI components
**Description:** Add user-friendly error messages.

**Steps:**
1. Wrap service calls in try-except
2. Show QMessageBox for critical errors
3. Show status bar messages for warnings
4. Log all errors with stack traces
5. Handle common errors:
   - SDK not found
   - Camera not found
   - Connection failed
   - Parameter out of range

### Task 5.3: Add Logging Integration
**Duration:** 30 minutes
**Dependencies:** All components
**Description:** Add comprehensive logging.

**Steps:**
1. Add loggers:
   - `logging.getLogger("camera.sdk")`
   - `logging.getLogger("camera.service")`
   - `logging.getLogger("camera.ui")`
2. Log all camera operations:
   - 连接/断开
   - 参数更改
   - 预设保存/加载
   - 错误和异常
3. Configure log levels in AppConfig

### Task 5.4: Final Testing
**Duration:** 30 minutes
**Dependencies:** All tasks complete
**Description:** End-to-end test.

**Test Checklist:**
1. ✅ 应用启动，CameraService 初始化
2. ✅ 相机发现返回设备列表
3. ✅ 连接相机成功
4. ✅ 开始预览，显示帧
5. ✅ 调整参数生效
6. ✅ 保存预设到文件
7. ✅ 加载预设，参数更新
8. ✅ 删除预设成功
9. ✅ 断开相机，资源释放
10. ✅ 会话超时，自动清理
11. ✅ 错误提示正确显示
12. ✅ 日志记录完整

**End of Phase 5**: Feature complete and production-ready

## 总结

**总时长**: 10-13 小时
**关键依赖**: Task 1.1 → 1.2 → 2.1 → 2.3 → 3.1 → 3.3 → 5.1
**风险点**:
- 需要真实海康相机测试
- 线程同步问题
- UI 性能优化

**交付物**:
- 完整的相机SDK集成
- CameraService API
- CameraPage UI
- 预设管理系统
- 完整的测试覆盖
