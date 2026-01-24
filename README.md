# SMART-VISION 工业视觉系统

基于 PySide6 的工业视觉桌面应用，提供登录认证、相机管理与工艺执行等能力。

## 使用指南

### 创建虚拟环境（venv）

- Windows：
  - `python -m venv venv`
  - `venv\Scripts\activate`
  - `pip install -r requirements.txt`

- Linux/macOS：
  - `python -m venv venv`
  - `source venv/bin/activate`
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
