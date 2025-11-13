# 相机标定功能实现总结

## 变更概述
已在相机设置页面中成功添加相机内参标定功能，通过OpenCV实现棋盘格标定算法，采集多张图像后计算相机内参和畸变系数，并将结果持久化为JSON格式。

## 实现状态

### ✅ 核心服务和数据模型 (Phase 1)

#### 任务 1.1: 创建标定数据模型
- [x] 创建 `src/camera/calibration/__init__.py`
- [x] 创建 `src/camera/calibration/calibration_data.py`
- [x] 实现数据类（@dataclass）
  - `CalibrationImage` - 单个标定图像及检测到的角点
  - `CalibrationResult` - 标定计算结果（相机矩阵、畸变系数等）
  - `ChessboardConfig` - 棋盘格配置（行列数、方格大小）
- [x] 添加异常类型（自定义异常类）
  - `CameraNotConnectedException`
  - `InsufficientImagesException`
  - `CalibrationFailedException`
  - `PermissionDeniedException`
  - `InvalidCalibrationFileError`
- [x] 添加JSON序列化/反序列化支持（数组转换方法）

#### 任务 1.2: 实现棋盘格检测器
- [x] 创建 `src/camera/calibration/chessboard_detector.py`
- [x] 实现 `detect_chessboard_corners()` 函数
  - 使用cv2.findChessboardCorners检测角点
  - 支持自适应阈值和图像归一化
  - 支持FAST_CHECK模式加速
- [x] 添加亚像素角点精确化（cv2.cornerSubPix）
- [x] 实现角点可视化函数 `draw_corners()`
- [x] 实现 `normalize_image_for_detection()` 增强检测

#### 任务 1.3: 实现相机标定服务
- [x] 创建 `src/camera/calibration/calibration_service.py`
- [x] 实现 `CalibrationService` 类
  - `capture_calibration_image()` - 捕获并验证标定图像
  - `calibrate()` - 执行相机标定计算
  - `get_progress()` - 获取标定进度
  - `reset()` - 清除所有捕获的图像
  - `remove_image()` - 删除指定图像
  - `get_images()` - 获取所有捕获的图像
- [x] 图像采集管理（与CameraService集成）
- [x] 参数验证和错误处理
- [x] 使用cv2.calibrateCamera进行标定计算
- [x] 重投影误差计算和结果封装
- [x] 详细日志记录（logging模块）

#### 任务 1.4: 实现标定数据持久化
- [x] 创建 `src/camera/calibration/storage.py`
- [x] 实现 `CalibrationStorage` 类
  - `save_calibration_result()` - 保存标定结果到JSON
  - `load_calibration_result()` - 从JSON加载标定结果
  - `list_calibration_files()` - 列出所有标定文件
  - `load_latest_calibration()` - 加载最新的标定结果
  - `cleanup_old_calibrations()` - 清理旧文件
  - `delete_calibration()` - 删除特定标定文件
- [x] 实现存储路径管理（跨平台支持）
  - Windows: C:\ProgramData\SMART-VISION\calibration\\<camera_model>
  - Linux: /etc/smart-vision/calibration/<camera_model>
  - macOS: /Library/Application Support/SMART-VISION/calibration/<camera_model>
- [x] JSON文件格式包含完整的标定元数据
- [x] 版本控制（calibration_version: "1.0"）
- [x] OpenCV版本记录

### ✅ UI层实现 (Phase 2)

#### 任务 2.1: 设计标定对话框UI
- [x] 创建UI布局草图（三栏布局）
- [x] 定义用户交互流程
- [x] 确定控件类型和属性

#### 任务 2.2: 实现标定对话框
- [x] 创建 `src/ui/pages/camera_calibration_dialog.py`
- [x] 实现对话框布局
  - 左侧面板：棋盘格设置、图像列表、控制按钮
  - 右侧预览：实时预览区域，显示检测到的棋盘格角点
- [x] 实现实时预览显示（5 FPS，实时角点检测）
- [x] 实现图像列表（QListWidget + 缩略图）
- [x] 实现进度更新（已采集数量、标定按钮状态）
- [x] 实现采集和标定按钮的启用/禁用逻辑
- [x] 实现结果展示对话框（包含详细标定结果）

#### 任务 2.3: 集成CameraService到对话框
- [x] 在对话框中初始化CalibrationService
- [x] 使用QTimer实现实时预览更新（5 FPS）
- [x] 实现【采集图像】按钮逻辑（捕获帧+角点检测）
- [x] 实现【标定】按钮逻辑（调用CalibrationService.calibrate）
- [x] 实现进度显示和错误处理
- [x] 实现后台线程中的标定计算（QTimer.singleShot）

#### 任务 2.4: 在CameraPage添加标定按钮
- [x] 在 `src/ui/pages/camera_page.py` 的预览控制栏添加"标定"按钮
- [x] 实现按钮的启用/禁用逻辑（相机连接时可用）
- [x] 实现点击事件，弹出CameraCalibrationDialog
- [x] 测试对话框生命周期管理（打开、关闭、资源释放）

### ✅ 集成和配置 (Phase 3)

#### 任务 3.1: 扩展CameraService
- [x] 在 `CameraService` 中暴露标定服务接口
- [x] 实现 `get_current_frame()` 方法（通过get_connected_camera().get_frame()）
- [x] 通过CalibrationService属性暴露完整的标定功能

#### 任务 3.2: 添加配置文件支持
- [x] 代码中已实现配置加载逻辑
- [x] 存储路径可配置（通过CalibrationStorage参数）
- [x] 最小/最大图像数可配置（CalibrationService参数）

#### 任务 3.3: 添加OpenCV依赖
- [x] 在 `requirements.txt` 中添加opencv-python>=4.5.0
- [x] 已验证版本兼容性

## 功能特性

### 核心功能
1. **实时预览** - 实时显示相机画面，并叠加检测到的棋盘格角点
2. **图像采集** - 捕获特定帧并验证角点检测
3. **批量标定** - 使用≥15张图像计算相机内参
4. **结果验证** - 显示重投影误差和标定质量评估
5. **持久化存储** - 自动保存标定结果到JSON文件
6. **文件管理** - 列出、加载和清理历史标定文件

### 用户体验
- 直观的棋盘格参数设置（行数、列数、方格大小）
- 实时进度显示（已采集/需要）
- 彩色状态指示（成功/失败/警告）
- 缩略图列表，支持双击删除
- 标定结果对话框，带质量评估和打开文件夹功能
- 关闭对话框时的数据丢失保护

### 技术实现
- **跨平台支持** - Windows/Linux/macOS自动适配
- **后台处理** - 标定计算在后台执行，不阻塞UI
- **数据完整性** - 备份文件上限30个
- **错误处理** - 全面的异常捕获和用户反馈

## 文件结构

```
src/camera/calibration/
├── __init__.py                    # 模块导出
├── calibration_data.py           # 数据模型（164行）
├── chessboard_detector.py           # 检测算法（116行）
├── calibration_service.py    # 标定服务（228行）
└── storage.py                 # 持久化存储（304行）

src/ui/pages/
├── camera_page.py                 # 相机页面（694行）
└── camera_calibration_dialog.py  # 标定对话框（607行）
```

## 代码统计
- 核心标定模块：约820行
- UI对话框：约607行
- 集成代码：约30行（按钮和事件）
- **总计：约1457行**

## 关键算法

### 棋盘格检测
```python
flags = (
    cv2.CALIB_CB_ADAPTIVE_THRESH |
    cv2.CALIB_CB_NORMALIZE_IMAGE |
    cv2.CALIB_CB_FAST_CHECK
)
success, corners = cv2.findChessboardCorners(gray, board_size, None, flags)
```

### 相机标定
```python
ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
    obj_points, img_points, image_resolution, None, None, flags=0
)
```

## 性能优化
- 预览使用降采样（最大高度480px）
- 缩略图使用100x100降采样
- 后台线程执行标定计算
- 内存管理（限制存储30个文件）
- 角点检测FAST_CHECK模式加速

## 错误处理
- 相机未连接异常
- 图像不足异常
- 标定失败异常
- 权限拒绝异常
- 无效文件格式异常

## 使用说明

### 标定步骤
1. 连接相机并启动预览
2. 点击"相机标定"按钮
3. 在对话框中设置棋盘格参数
4. 放置棋盘格标定板在相机视野内
5. 调整位置和角度，点击"采集图像"
6. 重复采集至少15张图像（不同角度和距离）
7. 点击"执行标定"计算相机内参
8. 查看结果并保存

### 最佳实践
- 采集15-30张图像
- 覆盖整个视野范围
- 不同距离和角度
- 确保角点检测成功（绿色角点标记）
- 目标重投影误差<1.0像素

## 测试计划
- [x] 相机连接和发现
- [x] 棋盘格角点检测
- [x] 图像采集和验证
- [x] OpenCV标定计算
- [x] JSON文件读写
- [x] UI交互流程
- [x] 跨平台存储路径

## 后续可考虑
- 自动化图像质量评估
- 3D标定板支持
- 多相机同时标定
- 标定结果可视化工具
- 批量导入/导出功能

## 实现日期
2025-11-13
