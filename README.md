# 工业视觉登录页面

基于 PySide6 创建的工业视觉软件登录界面，严格遵循工业视觉 UI 设计规范。

## 功能特性

- ✅ 符合工业视觉 UI 设计规范的深色主题
- ✅ 左右分栏布局，左侧显示系统信息，右侧为登录表单
- ✅ 支持用户名/密码登录
- ✅ 语言切换功能（中文/英文）
- ✅ 记住用户名选项
- ✅ 摄像头连接状态显示
- ✅ 主题切换功能按钮
- ✅ 悬停和焦点状态的交互反馈

## 设计规范

- **主色调**: 深石墨色 `#1A1D23` 和钢铁灰 `#1F232B`
- **强调色**: 悬停橙色 `#FF8C32`
- **文本颜色**: 北极白 `#F2F4F8` 和冷灰色 `#8C92A0`
- **字体**: 无衬线字体，标题和状态信息使用全大写
- **布局**: 严格对齐，合理留白，工业质感

## 运行要求

- Python 3.8+
- PySide6

## 环境设置

### 方法1: 自动设置虚拟环境（推荐）
```bash
# 运行自动设置脚本
python setup_env.py

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 激活虚拟环境（Linux/Mac）
source venv/bin/activate

# 运行登录页面
python login_page.py
```

### 方法2: 手动安装依赖
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 激活虚拟环境（Linux/Mac）
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行登录页面
python login_page.py
```

## 快速开始（无需虚拟环境）

如果你不想使用虚拟环境，可以直接安装依赖：

```bash
pip install PySide6==6.8.0
python login_page.py
```

## 界面预览

登录界面包含以下主要组件：

### 左侧面板
- **SMART-VISION** 系统标题
- 版本信息显示
- 摄像头连接状态列表
- 状态指示灯（绿色=已连接，灰色=未连接）

### 右侧面板
- **USER LOGIN** 登录表单标题
- 用户名输入框（默认占位符: admin）
- 密码输入框（遮蔽显示）
- 语言选择下拉框（中/English）
- "Remember username" 复选框
- **LOGIN** 橙色主按钮
- 底部 Preset 和 Theme 功能按钮

## 交互特性

- 所有输入框支持焦点状态，边框变为橙色
- 登录按钮支持悬停效果
- 底部按钮支持边框高亮
- 符合工业软件的操作习惯

## 文件结构

```
05ui-poc/
├── login_page.py          # 登录页面主程序
├── run_login.py          # 启动脚本
├── setup_env.py          # 虚拟环境自动设置脚本
├── requirements.txt      # Python依赖库列表
├── run.bat              # Windows快速启动脚本
├── run.sh               # Linux/Mac快速启动脚本
├── ui_design_guidelines.md  # UI设计规范文档
├── login.jpg             # 参考设计图片
└── README.md             # 说明文档
```

## 快速启动方式

### Windows用户
双击 `run.bat` 文件即可自动设置环境并启动

### Linux/Mac用户
```bash
./run.sh
```

### 虚拟环境使用
```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 退出虚拟环境
deactivate
```

## 技术实现

- **框架**: PySide6 (Qt6 Python 绑定)
- **布局管理**: QSplitter 实现左右分栏
- **样式系统**: QSS (Qt Style Sheets)
- **响应式设计**: 固定尺寸 1200x700，适合工业显示设备

## 后续扩展

- 添加实际的用户认证逻辑
- 连接数据库验证用户信息
- 实现主题切换功能
- 添加多语言支持
- 集成摄像头连接状态检测
- 添加预设配置功能