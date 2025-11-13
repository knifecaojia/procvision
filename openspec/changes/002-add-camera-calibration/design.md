# 相机标定功能设计

## 架构设计

### 整体架构
```
src/camera/
├── calibration/
│   ├── __init__.py
│   ├── calibration_service.py  # 标定服务核心逻辑
│   ├── calibration_data.py     # 标定数据结构
│   └── chessboard_detector.py  # 棋盘格检测器
└── camera_service.py           # 扩展现有服务

src/ui/pages/
└── camera_calibration_dialog.py # 标定对话框

config/calibration/              # 标定结果存储目录
```

### 组件交互
```
CameraPage (UI)
    └─> CalibrationDialog (弹出对话框)
         ├─> CameraService (获取实时帧)
         ├─> CalibrationService (执行标定逻辑)
         └─> CalibrationStorage (持久化结果)
```

## 详细设计

### 1. 相机标定服务 (CalibrationService)

**核心功能：**
- 管理标定图像集合
- 检测棋盘格角点
- 执行相机标定算法
- 计算标定质量指标

**主要接口：**
```python
class CalibrationService:
    def __init__(self, camera_service: CameraService):
        self.camera_service = camera_service
        self.calibration_images: List[CalibrationImage] = []

    def capture_calibration_image(self) -> bool:
        """捕获并验证当前相机帧作为标定图像"""
        pass

    def detect_chessboard(self, image: np.ndarray, board_size: Tuple[int, int]) -> bool:
        """检测图像中的棋盘格角点"""
        pass

    def calibrate(self, board_size: Tuple[int, int], square_size: float) -> CalibrationResult:
        """执行相机标定计算"""
        pass

    def get_progress(self) -> Tuple[int, int]:
        """返回(已采集数量, 需要数量)"""
        pass
```

**标定流程：**
1. 对每张采集的图像进行棋盘格检测
2. 收集足够的角点数据（≥15张有效图像）
3. 构建世界坐标系和图像坐标系的点对应关系
4. 调用cv2.calibrateCamera计算内参
5. 计算重投影误差评估标定质量

### 2. 标定数据模型

```python
@dataclass
class CalibrationImage:
    """单张标定图像数据"""
    timestamp: datetime
    image_data: np.ndarray
    corners_detected: Optional[np.ndarray]
    board_size: Tuple[int, int]

@dataclass
class CalibrationResult:
    """标定结果数据"""
    timestamp: datetime
    board_size: Tuple[int, int]
    square_size: float
    image_resolution: Tuple[int, int]
    camera_matrix: np.ndarray  # 3x3
    distortion_coeffs: np.ndarray  # 5x1 or 8x1
    reprojection_error: float
    total_images: int
    valid_images: int

@dataclass
class ChessboardConfig:
    """棋盘格配置参数"""
    rows: int  # 内角点行数
    cols: int  # 内角点列数
    square_size_mm: float  # 方格实际大小（毫米）
```

### 3. 标定对话框 (CameraCalibrationDialog)

**UI布局：**
```
┌─────────────────────────────────────────┐
│         相机内参标定                     │
├─────────────────┬───────────────────────┤
│                 │                       │
│  【棋盘格设置】  │                       │
│  行数: [9]      │     实时预览区域       │
│  列数: [6]      │                       │
│  方格大小: [25] │                       │
│                 │                       │
│  【采集的图像】  │                       │
│  ┌───────────┐  │                       │
│  │ 缩略图列表 │  │                       │
│  │ (15 needed)│  │                       │
│  └───────────┘  │                       │
│                 │                       │
│  【采集图像】    │                       │
│  【标定】        │                       │
│                 │                       │
└─────────────────┴───────────────────────┘
```

**交互逻辑：**
1. 打开对话框时显示实时相机预览
2. 用户可以调整棋盘格参数（行数、列数、方格大小）
3. 【采集图像】按钮：
   - 捕获当前帧
   - 自动检测棋盘格角点
   - 成功则添加到左侧列表（显示缩略图）
   - 失败则提示用户重新摆放棋盘格
4. 当采集≥15张有效图像后，【标定】按钮启用
5. 点击【标定】：
   - 显示进度条
   - 执行标定计算
   - 显示结果和重投影误差
   - 保存JSON文件
   - 可选择应用标定参数

### 4. 数据持久化

**存储格式 (JSON)：**
```json
{
  "calibration_id": "20241113_143022",
  "timestamp": "2024-11-13T14:30:22.123456",
  "camera_model": "MV-CA050-10GM",
  "image_resolution": [2448, 2048],
  "board_size": [9, 6],
  "square_size_mm": 25.0,
  "camera_matrix": [[...], [...], [...]],
  "distortion_coefficients": [...],
  "reprojection_error": 0.523,
  "total_images": 18,
  "valid_images": 16,
  "calibration_version": "1.0"
}
```

**存储路径：**
- Windows: `C:\ProgramData\SMART-VISION\calibration\<camera_model>\`
- Linux: `/etc/smart-vision/calibration/<camera_model>/`
- 开发模式: `config/calibration/<camera_model>/`

### 5. 集成点

**CameraPage修改：**
1. 在预览控制栏添加"标定"工具按钮
2. 点击按钮弹出CameraCalibrationDialog

**CameraService扩展：**
```python
class CameraService:
    @property
    def calibration_service(self) -> Optional[CalibrationService]:
        if not self.current_camera:
            return None
        return CalibrationService(self)

    def get_current_frame(self) -> Optional[FrameData]:
        """获取当前帧（用于标定）"""
        if not self.current_camera:
            return None
        return self.current_camera.get_frame()
```

## 关键技术决策

### 1. OpenCV版本选择

选择opencv-python>=4.5.0，理由：
- 稳定的相机标定API
- 支持亚像素角点检测
- 良好的性能
- 广泛社区支持

### 2. 棋盘格检测算法

```python
def detect_chessboard_corners(image, board_size):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 查找棋盘格角点
    ret, corners = cv2.findChessboardCorners(
        gray, board_size, None,
        cv2.CALIB_CB_ADAPTIVE_THRESH +
        cv2.CALIB_CB_NORMALIZE_IMAGE +
        cv2.CALIB_CB_FAST_CHECK
    )

    if ret:
        # 亚像素角点精确化
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    return ret, corners
```

### 3. 标定质量控制

**质量标准：**
- 有效图像数量≥15张
- 重投影误差<1.0像素（良好）
- 相机矩阵合理性检查
- 畸变系数范围检查

**用户体验：**
- 实时显示已采集图像数量和质量
- 标定完成后显示详细报告
- 提供重新标定选项

### 4. 性能考虑

**内存管理：**
- 标定过程中不在内存中存储过多全尺寸图像
- 缩略图使用降采样版本（200x200）
- 原始图像数据按需加载

**计算性能：**
- 标定计算在后台线程执行，避免UI卡顿
- 大型相机传感器（2000万像素以上）在缩略图上进行角点检测预览

## 错误处理

| 错误场景 | 处理方式 | 用户提示 |
|---------|---------|---------|
| 未连接相机 | 禁止打开标定对话框 | "请先连接相机" |
| 棋盘格检测失败 | 跳过该图像，提示用户重新摆放 | "未检测到棋盘格，请调整位置" |
| 采集图像数不足 | 禁用标定按钮 | 显示进度 "8/15" |
| 标定计算失败 | 显示错误详情 | "标定失败: 角点数据不足" |
| 文件存储失败 | 显示错误，建议检查权限 | "保存失败，请检查磁盘空间" |

## 测试策略

1. **单元测试** (src/tests/camera/)
   - 棋盘格角点检测测试
   - 标定参数计算测试
   - JSON序列化/反序列化测试

2. **集成测试**
   - 完整标定流程测试
   - UI交互测试（使用pytest-qt）
   - 实时帧捕获和角点检测

3. **手动测试检查表**
   - [ ] 连接相机后"标定"按钮可用
   - [ ] 实时预览正常显示
   - [ ] 棋盘格角点检测准确
   - [ ] 采集15张图像后"标定"按钮启用
   - [ ] 标定计算成功，重投影误差<1.0
   - [ ] JSON文件正确生成并包含所有数据
   - [ ] 异常场景处理（相机断开、检测失败等）

## 未来扩展

1. **外参标定**：支持多相机系统的外参标定
2. **验证工具**：标定完成后提供验证界面
3. **参数管理**：将标定参数集成到相机预设系统
4. **自动标定**：支持自动化标定流程（如协作机器人手持棋盘格）

## 依赖项

**新增依赖：**
```
opencv-python>=4.5.0
numpy>=1.21.0  # 已存在
```

**兼容性：**
- Windows 10/11
- Python 3.8+
- HiKSDK相机驱动（已集成）
