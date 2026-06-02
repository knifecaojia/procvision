import sys
import os
import sysconfig
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
datas.append(('config.json', '.'))

binaries = []
base_dir = sysconfig.get_config_var('installed_base')

dlls_dir = os.path.join(base_dir, 'DLLs')
libffi_dll = os.path.join(dlls_dir, 'libffi-8.dll')
if os.path.exists(libffi_dll):
    binaries.append((libffi_dll, '.'))

conda_lib_bin = os.path.join(base_dir, 'Library', 'bin')
if os.path.isdir(conda_lib_bin):
    for dll_name in [
        'ffi.dll', 'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
        'liblzma.dll', 'LIBBZ2.dll', 'libexpat.dll', 'sqlite3.dll',
    ]:
        dll_path = os.path.join(conda_lib_bin, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=binaries,
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
    console=True,
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
