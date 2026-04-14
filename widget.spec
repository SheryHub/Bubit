# -*- mode: python ; coding: utf-8 -*-

# PyInstaller spec file for Bubit
# Optimized for Windows with minimal footprint

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
	   'pyaudiowpatch',
        'websocket',
        'numpy',
        'scipy.signal',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Only exclude heavy GUI/graphics libs
        'matplotlib',
        'matplotlib.backends',
        'matplotlib.pyplot',
        'PIL',  # Only if not using images
        'tkinter.test',
        'tkinter.tix',
        'tkinter.scrolledtext',
        # Testing modules
        'pytest',
        'doctest',
        'pdb',
        # Documentation
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Bubit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Strip debug symbols -> might also be the issue for dll issues
    upx=False,    # Compress with UPX if available -> seems to have dll issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Bubit.ico'],
    version='version.txt',
)
