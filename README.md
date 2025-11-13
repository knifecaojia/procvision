# SMART-VISION 工业视觉系统

基于 PySide6 的工业视觉桌面应用，包含用户认证、相机管理、参数预设、相机标定等完整功能，遵循工业视觉 UI 设计规范。

## 技术栈

- Python 3.8+
- PySide6 6.8.0.2
- OpenCV 4.5.0+
- NumPy 1.21.0+
- bcrypt 4.2.0
- 海康威视 MVS SDK（可选）

## 核心功能

- 登录认证：用户名/密码、语言切换（中文/英文）、记住用户名、安全哈希存储
- 相机管理：发现与连接、实时预览、参数调节、预设管理、截图
- 相机标定：棋盘格角点检测、≥15 张采集、内参/畸变系数计算、重投影误差评估、历史管理
- UI 交互：工业深色主题、悬停/焦点反馈、参数滑块联动、进度与状态提示
- 工艺执行：工艺流程页面与执行窗口（进度监控）

## 目录结构（精简）

```
05ui-poc/
├── src/
│  ├── core/                 # 应用核心（入口、配置、会话）
│  │  ├── app.py             # 应用入口（main）
│  │  ├── config.py          # 配置与环境变量
│  │  └── session.py         # 会话管理
│  ├── auth/                 # 认证模块（模型、服务、存储）
│  ├── camera/               # 相机模块（服务、后端、标定）
│  │  └── calibration/       # 标定数据/算法/持久化
│  ├── ui/                   # UI（主窗体、登录、页面与组件）
│  │  ├── pages/camera_calibration_dialog.py
│  │  └── styles/main_window.qss
│  └── utils/                # 校验与通用工具
├── scripts/create_default_user.py
├── requirements.txt
├── run_app.py               # 启动完整应用
├── run_login.py             # 登录页面预览
├── run.bat / run.sh         # 一键启动登录页（含 venv）
├── setup_env.py             # 自动创建 venv 并安装依赖
├── config/app_config.json   # 运行时配置（自动生成/更新）
├── test_login.py / test_model_card.py
└── README.md
```

## 安装与运行

- 自动安装（推荐）
  - `python setup_env.py`
  - Windows 激活：`venv\Scripts\activate`
  - Linux/macOS 激活：`source venv/bin/activate`

- 手动安装
  - `python -m venv venv && <激活虚拟环境>`
  - `pip install -r requirements.txt`

- 快速试用（无需 venv）
  - `pip install PySide6==6.8.0.2 opencv-python>=4.5.0 numpy>=1.21.0 bcrypt==4.2.0`

## 启动方式

- 完整应用：`python run_app.py`
- 登录页面：`python run_login.py`，或 Windows `./run.bat`，Linux/macOS `./run.sh`

## 默认账户

- 创建默认用户：`python scripts/create_default_user.py`
- 默认用户名/密码：`admin` / `admin123`（仅用于开发测试，生产请修改）

## 相机标定使用

- 在“相机页面”进入“标定”对话框，设置棋盘格行/列与方格尺寸
- 采集 ≥15 张不同角度/距离的图像，执行标定并查看重投影误差（建议 <1.0 像素）
- 结果自动保存为 JSON，按相机型号分目录管理

保存路径（系统自动选择）：
- Windows：`C:\ProgramData\SMART-VISION\calibration\<相机型号>\YYYYMMDD_HHMMSS_calibration.json`
- Linux：`/etc/smart-vision/calibration/<相机型号>/`
- macOS：`/Library/Application Support/SMART-VISION/calibration/<相机型号>/`

## 配置与环境变量

- `SMART_VISION_DEBUG`（bool）：启用调试模式
- `SMART_VISION_DEV_MODE`（bool）：开发模式
- `SMART_VISION_DB_PATH`（str）：认证数据库路径（默认 `data/auth.db`）
- `SMART_VISION_LOG_LEVEL`（str）：日志级别（INFO/DEBUG 等）
- `SMART_VISION_SESSION_TIMEOUT`（int）：会话超时小时数
- `SMART_VISION_LANGUAGE`（str）：默认语言（“中”/“English”）
- `SMART_VISION_CAMERA_SDK_PATH`（str）：工业相机 SDK 路径

示例（Windows）：
```
set SMART_VISION_LOG_LEVEL=DEBUG
set SMART_VISION_LANGUAGE=English
python run_app.py
```

## 日志与数据

- 日志文件：`logs/app.log`
- 认证数据库：`data/auth.db`（自动创建）
- 相机预设：`data/camera_presets/`

## 测试

- 登录模块快速检查：`python test_login.py`
- 组件演示（模型卡片）：`python test_model_card.py`

## 许可与支持

- Copyright (c) 2025 SMART-VISION Project
- 问题反馈与建议：请提交 Issue 或联系维护团队