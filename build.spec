import sys
import os
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.datastruct import Tree

hiddenimports = []
hiddenimports += collect_submodules('PySide6')
for m in ['MvCameraControl_class', 'CameraParams_header', 'MvErrorDefine_const', 'PixelType']:
    try:
        __import__(m)
        hiddenimports.append(m)
    except Exception:
        pass

datas = []
datas.append(('config/app_config.json', 'config'))
datas.append(('config.json', '.'))

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='SouthwestUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *( [Tree('runtime', prefix='runtime')] if os.path.exists('runtime') else [] ),
    Tree('src/ui/styles/themes', prefix='src/ui/styles/themes'),
    Tree('src/assets', prefix='src/assets'),
    Tree('data/mock', prefix='data/mock'),
    name='SouthwestUI',
)
