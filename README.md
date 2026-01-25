# SMART-VISION 工业视觉系统

基于 PySide6 的工业视觉桌面应用，提供登录认证、相机管理与工艺执行等能力。

## 强制运行环境要求

- 操作系统：Windows 10/11 64 位
- Python：3.12.x（源码运行与打包 EXE 均按 Python 3.12 运行时设计）
- 网络：默认离线环境（不依赖互联网；算法部署不使用 conda 机制）
- 运行目录：
  - 源码运行：建议始终通过 `python run_app.py` 启动（会将工作目录切到项目根目录）
  - EXE 运行：工作目录为 EXE 所在目录（配置与算法目录均相对该目录）

## 配置文件（统一）

项目统一使用单一配置文件：

- `config.json`（项目根目录 / EXE 同级）：包含 UI/运行偏好（server/storage/general/theme）以及核心业务配置（auth/database/logging/camera/network 等）

为避免“保存路径与加载路径不一致”，启动入口会在源码与 EXE 模式下统一工作目录，并确保发布包内置的默认配置会复制到可写位置。

## 算法包与部署要求（强制）

### 算法包命名

- 算法包文件名必须为：`<name>-<version>.zip`（例如 `demo2-v3.0.1.zip`）

### 算法包内容

- `manifest.json`：必须包含
  - `entry_point`：算法入口（Runner 通过 `python -m procvision_algorithm_sdk.adapter --entry <entry_point>` 调用）
  - `supported_pids`：支持的 PID 列表（用于任务/工艺绑定）
- `wheels/`：离线依赖 wheel 包目录
- `requirements.txt`：依赖清单（与 wheels 配合离线安装）

### 部署行为（离线）

- 解压到：`algorithms/deployed/<name>-<version>/`
- 创建虚拟环境：`algorithms/deployed/<name>-<version>/__procvision_env/`
- 离线安装依赖：使用 `--no-index --find-links <wheels_dir>` 从 wheels 安装 `requirements.txt`
- 部署注册表：`algorithms/registry.json`（用于判断“是否已安装/可执行”，并支持卸载）

## 使用指南

### 创建虚拟环境（venv，Python 3.12）

- Windows：
  - `python -m venv venv`
  - `venv\Scripts\activate`
  - `pip install -r requirements.txt`

### 打包为 Windows EXE（PyInstaller，单目录输出到 dist）

- 安装 PyInstaller：
  - `pip install pyinstaller`

- 使用 spec 构建（推荐，资源与依赖收集更稳定）：
  - `python -m PyInstaller --clean -y --workpath build --distpath dist build.spec`

- 产物位置：
  - `dist/SouthwestUI/SouthwestUI.exe`

- 可选：如项目根目录存在 `runtime/`，打包时会一并收集到发布包中（用于随包 Python/venv 等运行时资产）。

### 启动完整应用

- `python run_app.py`

## 许可与支持

- Copyright (c) 2025 SMART-VISION Project
- 问题反馈与建议：请提交 Issue 或联系维护团队
