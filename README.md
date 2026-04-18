# SMART-VISION 工业视觉系统

基于 PySide6 的工业视觉桌面应用，提供登录认证、相机管理与工艺执行等能力。

## 目录

- [强制运行环境要求](#强制运行环境要求)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [编译 EXE（详细说明）](#编译-exe详细说明)
- [配置文件说明](#配置文件说明)
- [算法包与部署要求](#算法包与部署要求)
- [常见问题](#常见问题)

---

## 强制运行环境要求

| 项目     | 要求                                    |
| -------- | --------------------------------------- |
| 操作系统 | Windows 10/11 64 位                     |
| Python   | 3.12.x（源码运行与打包 EXE 均按此设计） |
| 网络     | 默认离线环境（不依赖互联网）            |
| 内存     | 建议 8GB+                               |
| 磁盘     | 500MB+ 可用空间                         |

---

## 项目结构

```
05ui-poc/
├── run_app.py              # 应用入口
├── build.spec              # PyInstaller 打包配置
├── config.json             # 主配置文件
├── requirements.txt        # Python 依赖
├── src/
│   ├── core/               # 核心模块（应用初始化、配置）
│   ├── ui/                 # 用户界面
│   │   ├── pages/          # 页面组件
│   │   ├── windows/        # 窗口组件
│   │   ├── components/     # 通用组件
│   │   └── styles/         # 样式与主题
│   ├── camera/             # 相机服务
│   ├── runner/             # 算法运行引擎
│   ├── services/           # 业务服务
│   ├── auth/               # 认证模块
│   └── assets/             # 静态资源
├── data/
│   ├── mock/               # 模拟数据
│   └── camera_presets/     # 相机预设配置
└── config/                 # 配置目录
```

---

## 快速开始

### 1. 创建虚拟环境

```powershell
# 创建虚拟环境（Python 3.12）
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动应用

```powershell
python run_app.py
```

默认登录凭据：

- 用户名：`admin`
- 密码：`admin123`

---

## 编译 EXE（详细说明）

### 前置条件

1. **确保 Python 版本正确**：必须使用 Python 3.12.x

   ```powershell
   python --version
   # 输出应为 Python 3.12.x
   ```
2. **确保虚拟环境已激活**：

   ```powershell
   venv\Scripts\activate
   ```
3. **确保依赖已完整安装**：

   ```powershell
   pip install -r requirements.txt
   ```

### 编译步骤

#### 方法一：使用 build.spec（推荐）

```powershell
# 清理并编译
python -m PyInstaller --clean -y --workpath build --distpath dist build.spec
```

**参数说明**：

| 参数                 | 说明                 |
| -------------------- | -------------------- |
| `--clean`          | 清理缓存，重新构建   |
| `-y`               | 覆盖已有输出目录     |
| `--workpath build` | 临时构建文件存放目录 |
| `--distpath dist`  | 最终输出目录         |

#### 方法二：直接使用 PyInstaller 命令

```powershell
pyinstaller --clean -y `
    --name SouthwestUI `
    --windowed `
    --add-data "config.json;." `
    --add-data "src/ui/styles/themes;src/ui/styles/themes" `
    --add-data "src/assets;src/assets" `
    --add-data "data/mock;data/mock" `
    --hidden-import=PySide6 `
    run_app.py
```

### 编译产物

编译完成后，产物位于：

```
dist/
└── SouthwestUI/
    ├── SouthwestUI.exe    # 主执行文件
    ├── _internal/         # 依赖库和资源
    │   ├── PySide6/
    │   ├── src/
    │   │   ├── ui/styles/themes/
    │   │   └── assets/
    │   └── data/mock/
    └── config.json        # 配置文件（首次运行时自动复制）
```

### 发布包准备

1. **打包发布目录**：

   ```powershell
   # 将 dist/SouthwestUI 整个目录打包为 ZIP
   Compress-Archive -Path dist\SouthwestUI -DestinationPath SouthwestUI-v1.0.0.zip
   ```
2. **可选：添加算法包**：

   - 在发布目录中创建 `algorithms/` 目录
   - 将算法包放入该目录

### 编译配置说明（build.spec）

```python
# build.spec 关键配置解析

a = Analysis(
    ['run_app.py'],           # 入口文件
    pathex=['.'],             # 搜索路径
    datas=[
        ('config.json', '.'), # 包含配置文件
    ],
    hiddenimports=collect_submodules('PySide6'),  # 隐式导入
)

exe = EXE(
    ...
    name='SouthwestUI',       # 输出文件名
    console=False,            # 隐藏控制台窗口
)

coll = COLLECT(
    ...
    Tree('src/ui/styles/themes', prefix='src/ui/styles/themes'),  # 主题文件
    Tree('src/assets', prefix='src/assets'),                      # 资源文件
    Tree('data/mock', prefix='data/mock'),                        # 模拟数据
    name='SouthwestUI',
)
```

### 编译常见问题

| 问题                                               | 解决方案                                    |
| -------------------------------------------------- | ------------------------------------------- |
| `ModuleNotFoundError: No module named 'PySide6'` | 确保在虚拟环境中安装了依赖                  |
| `Permission denied`                              | 关闭杀毒软件或以管理员权限运行              |
| 打包后运行闪退                                     | 检查 `config.json` 是否正确复制，查看日志 |
| 文件过大（>500MB）                                 | 正常现象，PySide6 依赖较多                  |

---

## 配置文件说明

项目使用 `config.json` 作为统一配置文件。

### 主要配置项

```json
{
  "ui": {
    "window_width": 1050,
    "window_height": 700,
    "colors": { ... },
    "font_family": "Arial"
  },
  "general": {
    "auto_start_next": false,
    "result_prompt_position": "center",
    "draw_boxes_ok": true,
    "draw_boxes_ng": true,
    "theme": "dark",
    "ok_toast_duration": 2
  },
  "camera": {
    "preview_fps_limit": 30,
    "connection_timeout_ms": 5000
  },
  "network": {
    "base_url": "http://127.0.0.1:80",
    "timeout": 10
  }
}
```

### 配置项说明

| 配置项                             | 类型   | 说明                              |
| ---------------------------------- | ------ | --------------------------------- |
| `general.auto_start_next`        | bool   | 完成后自动开始下一产品            |
| `general.result_prompt_position` | string | 结果提示位置（center/top_left等） |
| `general.draw_boxes_ok`          | bool   | OK结果时绘制检测框                |
| `general.draw_boxes_ng`          | bool   | NG结果时绘制检测框                |
| `general.theme`                  | string | 主题（dark/light）                |
| `general.ok_toast_duration`      | int    | OK提示显示时长（秒）              |

---

## 算法包与部署要求

### 算法包命名

算法包文件名必须为：`<name>-<version>.zip`（例如 `demo2-v3.0.1.zip`）

### 算法包内容

| 文件/目录            | 说明                                           |
| -------------------- | ---------------------------------------------- |
| `manifest.json`    | 必须包含 `entry_point` 和 `supported_pids` |
| `wheels/`          | 离线依赖 wheel 包目录                          |
| `requirements.txt` | 依赖清单                                       |

### 部署路径

- 解压位置：`algorithms/deployed/<name>-<version>/`
- 虚拟环境：`algorithms/deployed/<name>-<version>/__procvision_env/`
- 注册表：`algorithms/registry.json`

---

## 常见问题

### Q: 如何切换主题？

A: 修改 `config.json` 中的 `general.theme` 为 `dark` 或 `light`。

### Q: 如何启用调试模式？

A: 设置 `config.json` 中的 `debug_mode: true`，可查看详细日志。

### Q: 相机无法连接？

A:

1. 检查相机是否正确连接
2. 确认海康威视 SDK 已安装
3. 查看 `logs/app.log` 日志文件

### Q: 编译后缺少文件？

A: 检查 `build.spec` 中的 `Tree` 配置是否包含所需目录。

### Q: 打包后 EXE 无法运行？

A:

1. 检查是否在虚拟环境中编译
2. 确认 `config.json` 在 EXE 同级目录
3. 查看日志文件排查错误

---

## 许可与支持

- Copyright (c) 2025 SMART-VISION Project
- 问题反馈与建议：请提交 Issue 或联系维护团队
