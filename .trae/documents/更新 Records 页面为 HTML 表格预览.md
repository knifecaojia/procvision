## 目标

* 将 GUI 入口 [run\_app.py](file:///f:/Ai-LLM/southwest/05ui-poc/run_app.py) 打包为单目录发布包，输出到 dist。

* 收集 PySide6/Qt 插件、QSS、字体、图标、JSON 配置与示例数据，确保开箱可运行。

## 资源清单

* QSS 主题：src/ui/styles/themes/**/**.qss

* 资源与字体：src/assets/\*\*（含 SourceHanSansSC-Normal-2.otf）

* 配置：config/app\_config.json、config.json

* 示例数据（如 UI依赖）：data/mock/\*\*.json

* 可选：海康 MVS SDK（若目标机使用摄像头功能）

## PyInstaller 方案

* 推荐使用 spec 文件，统一管理 datas 与隐藏导入：

```python
# build.spec（示例）
# 需在项目根目录执行：pyinstaller build.spec
import sys
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = []
# PySide6 自动有内置 hook；如遇动态导入，可用：
hiddenimports += collect_submodules('PySide6')

# 海康 MVS（旧版 SDK 模块名；若未安装则忽略打包失败，后续可移除）
for m in ['MvCameraControl_class','CameraParams_header','MvErrorDefine_const','PixelType']:
    try:
        __import__(m)
        hiddenimports.append(m)
    except Exception:
        pass

# 资源文件
_datas = []
_datas += collect_data_files('src/ui/styles', includes=['**/*.qss'],
                             dest='src/ui/styles')
_datas += collect_data_files('src/assets', includes=['**/*'],
                             dest='src/assets')
_datas += [('config/app_config.json', 'config'), ('config.json', '.')]
_datas += collect_data_files('data/mock', includes=['**/*.json'],
                             dest='data/mock')

block_cipher = None

a = Analysis(['run_app.py'],
             pathex=['.'],
             binaries=[],
             datas=_datas,
             hiddenimports=hiddenimports,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='SouthwestUI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False)
coll = COLLECT(exe,
              a.binaries,
              a.zipfiles,
              a.datas,
              name='SouthwestUI')
```

* 说明：

  * console=False 以 GUI 模式运行；若需要调试终端输出可设 True。

  * datas 使用目标目录保持相对路径一致，匹配代码里的路径查找。

  * hiddenimports 动态添加，避免 Qt/MVS 的隐藏导入问题。

## 构建命令

* 在项目根目录、激活虚拟环境后：

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --clean -y --workpath build --distpath dist build.spec
```

* 直接命令（不使用 spec）亦可，但维护成本高：

```bash
pyinstaller -y --clean --workpath build --distpath dist \
  --name SouthwestUI --noconfirm --windowed run_app.py \
  --add-data "src/ui/styles/themes;src/ui/styles/themes" \
  --add-data "src/assets;src/assets" \
  --add-data "config/app_config.json;config" \
  --add-data "config.json;." \
  --add-data "data/mock;data/mock" \
  --hidden-import PySide6 \
  --hidden-import MvCameraControl_class \
  --hidden-import CameraParams_header \
  --hidden-import MvErrorDefine_const \
  --hidden-import PixelType
```

* Windows 下 --add-data 以分号分隔 "源;目标"。

## 运行与验证

* 执行：dist/SouthwestUI/SouthwestUI.exe

* 验证：

  * UI 能启动，主题样式生效（QSS 与字体）

  * 配置加载正常（config/app\_config.json、config.json）

  * 示例数据页面是否正常（若依赖 data/mock）

  * 如启用海康摄像头功能：确保目标机已安装 MVS SDK，且其 Bin 路径在 PATH 或由应用代码的 os.add\_dll\_directory 找到。

## 常见问题与对策

* Qt 插件缺失（qwindows.dll）：设置环境变量 QT\_DEBUG\_PLUGINS=1 观察日志；确保 PyInstaller 收集 PySide6 plugins（内置 hook 通常可用）。

* 资源未找到：检查 datas 映射的目标目录是否与代码加载路径一致。

* 一些隐藏导入缺失：在 spec/命令中追加 --hidden-import。

* 海康 SDK 找不到 DLL：将 SDK 的 Bin\win64 路径加入系统 PATH，或在应用启动时通过 os.add\_dll\_directory 指定；也可将 SDK 复制到 dist/vendors 并在运行前设置 MVCAM\_COMMON\_RUNENV。

## 输出l

* 单目录发布包：dist/SouthwestUI/，包含 exe 与所有依赖文件，可直接分发与运行。

