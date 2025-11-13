# 相机标定功能提案

## 变更概述
在相机设置页面( `src/ui/pages/camera_page.py` )中增加相机内参标定功能，通过OpenCV实现棋盘格标定算法，采集多张图像后计算相机内参和畸变系数，并将结果存储为JSON格式。

## 变更范围

### 新增功能
1. **UI层** - 相机标定界面
   - 在相机页面添加"标定"按钮
   - 弹出标定对话框，包含：
     - 棋盘格规格设置（行数、列数、方格大小）
     - 图像采集区域（左侧QListWidget显示缩略图）
     - 【采集图像】按钮
     - 【标定】按钮（采集≥15张后自动启用）
     - 实时预览区域

2. **服务层** - 相机标定服务
   - 图像采集管理
   - 棋盘格角点检测（使用cv2.findChessboardCorners）
   - 相机标定计算（cv2.calibrateCamera）
   - 重投影误差计算
   - 标定结果验证

3. **存储层** - 标定数据持久化
   - JSON格式存储标定结果
   - 包含：标定时间、棋盘格规格、图像分辨率、相机矩阵、畸变系数、重投影误差
   - 存储路径： `config/calibration/` 或系统配置目录

### 技术栈新增
- **OpenCV (opencv-python)**: 用于图像处理和相机标定算法

### 影响范围
- `src/ui/pages/camera_page.py` - 添加标定按钮和触发逻辑
- `src/camera/` - 新增标定服务模块
- `config/app_config.json` - 添加标定配置
- `requirements.txt` - 添加opencv-python依赖

## 变更ID
002-add-camera-calibration

## 相关历史变更
- 001-integrate-hikvision-camera: 相机基础集成和预览功能
- 002-create-process-execution-window: 工艺流程执行界面

## 预期效果
用户可以在相机设置页面直接进行相机内参标定，无需外部工具，标定结果自动保存并可用于后续的图像校正和测量任务。
