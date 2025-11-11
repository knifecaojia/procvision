# Design: Hikvision Camera Integration Architecture

## 1. 系统架构概览

### 核心组件
```
src/
├── core/
│   ├── app.py              # 主应用，管理CameraService生命周期
│   ├── config.py           # 添加CameraConfig配置
│   └── session.py          # 集成相机会话清理
├── camera/                 # NEW: 相机SDK模块
│   ├── __init__.py
│   ├── backend.py          # 抽象基类
│   ├── camera_device.py    # 设备封装
│   ├── camera_manager.py   # 管理器
│   ├── camera_service.py   # NEW: 服务层
│   ├── preset_manager.py   # NEW: 预设管理
│   ├── types.py            # 类型定义
│   ├── exceptions.py       # 异常定义
│   └── hikvision_backend.py # 海康实现
└── ui/
    ├── pages/
    │   └── camera_page.py  # 相机页面
    └── components/
        └── slider_field.py # NEW: 滑块控件
```

## 2. 相机服务层设计

### CameraService 职责
- 封装所有相机操作，提供干净API
- 管理相机生命周期
- 处理参数管理
- 预设文件操作
- 错误处理和日志记录

### CameraService API

```python
class CameraService:
    def __init__(self, config: CameraConfig):
        """初始化服务"""
        self.config = config
        self.manager = CameraManager(sdk_path=config.sdk_path)
        self.current_camera: Optional[CameraDevice] = None
        self.preset_manager = PresetManager()

    # 相机生命周期
    def discover_cameras(self) -> List[CameraInfo]
    def connect_camera(self, camera_info: CameraInfo) -> bool
    def disconnect_camera(self) -> None

    # 参数管理
    def get_all_parameters(self) -> Dict[str, Any]
    def set_parameter(self, key: str, value: Any) -> bool
    def get_parameter_range(self, key: str) -> Tuple[float, float]

    # 预设管理
    def save_preset(self, name: str, user: User) -> bool
    def load_preset(self, name: str, camera_model: str) -> Optional[Dict]
    def list_presets(self, camera_model: str) -> List[str]

    # 流控制
    def start_preview(self) -> bool
    def stop_preview(self) -> None
    def is_streaming(self) -> bool
```

## 3. 线程模型

```
主线程 (UI)
  │
  ├─ CameraService (在主线程)
  │     └─ 调用 manager.connect()
  │     └─ 调用 camera.set_parameter()
  │     └─ 调用 preset_manager.save_preset()
  │
  └─ CameraPage
        │
        └─ PreviewWorker (QThread)
              │
              └─ camera.get_frame() 循环
              └─ 发射 frame_ready 信号
```

**线程安全策略**:
- BackendDevice 使用 threading.RLock 保护参数访问
- PreviewWorker 在独立线程运行
- UI 通过信号接收帧数据
- 参数更新通过同一把锁保护

## 4. UI 集成设计

### CameraPage 组件结构
```
CameraPage
  ├─ CameraService (构造时注入)
  ├─ PreviewWorker (QThread)
  ├─ 预览区域 QLabel
  ├─ 工具栏 QToolButton (连接/断开/预览/截图)
  ├─ 参数面板 SliderField
  │    ├─ 曝光时间
  │    ├─ 增益
  │    └─ 帧率
  └─ 状态面板
       ├─ 相机型号
       ├─ 连接状态
       └─ 实时 FPS
```

### 数据流
1. **连接相机**: 点击连接 → service.connect_camera() → UI 更新状态
2. **开始预览**: service.start_preview() → PreviewWorker 启动 → 帧信号 → QLabel 更新
3. **调整参数**: 拖动滑块 → service.set_parameter() → 相机生效 → 预览更新
4. **保存预设**: 点击保存 → service.save_preset() → JSON 写入文件

## 5. 预设文件存储

### 目录结构
```
data/
├── auth.db
└── camera_presets/
    └── {username}/           # 按用户隔离
        ├── MV-CA060-10GM/
        │   ├── Daylight.json
        │   └── LowLight.json
        └── MV-CE200-10GM/
            └── Indoor.json
```

### JSON 格式
```json
{
  "name": "Daylight Indoor",
  "camera_model": "MV-CA060-10GM",
  "user_id": 1,
  "user_name": "admin",
  "created_at": "2025-01-15T10:30:00Z",
  "parameters": {
    "ExposureTime": 5000,
    "Gain": 1.5,
    "AcquisitionFrameRate": 30.0
  }
}
```

## 6. 错误处理策略

| 错误类型 | 处理方式 | 用户提示 |
|---------|---------|---------|
| SDK 未找到 | 应用启动时检查，无法启动相机功能 | 状态栏显示 "SDK 未安装" |
| 相机连接失败 | 记录日志，返回 False | 对话框："连接失败，请检查相机" |
| 参数无效 | 捕获异常，记录日志 | 状态栏："参数超出范围" |
| 帧超时 | 记录警告，继续尝试 | FPS 显示 0 |
| 文件读写错误 | 记录错误，回退操作 | 对话框显示具体错误 |

## 7. 配置集成

### CameraConfig
```python
@dataclass
class CameraConfig:
    sdk_path: Optional[str] = None
    enable_preview: bool = True
    preview_fps_limit: int = 30
    auto_connect: bool = False
```

### 环境变量
- `SMART_VISION_CAMERA_SDK_PATH`: 覆盖 SDK 路径

## 8. 与现有系统集成

### Session Management
- 会话超时 → 自动断开相机
- 注销 → 清理相机资源
- 应用退出 → 保存配置

### Logging
- Logger 命名空间：camera.sdk, camera.service, camera.ui
- DEBUG: 帧统计
- INFO: 连接/断开
- WARNING: 参数错误
- ERROR: 严重错误

## 9. 性能考虑

- **帧率**: 目标 30 FPS @ 1920x1080
- **内存**: 帧缓冲区最多 3 帧
- **CPU**: 预览工作线程睡眠 1ms
- **UI 刷新**: 最大 60 FPS

## 10. 测试策略

### 需要真实硬件
- 需要至少一台海康相机用于测试
- 没有 mock fallback
- 测试环境必须安装 MVS SDK

### 测试场景
1. 相机发现
2. 连接/断开
3. 参数获取/设置
4. 预览启动/停止
5. 预设保存/加载
6. 错误处理
