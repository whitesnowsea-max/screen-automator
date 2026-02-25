# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Screen Automator (Windows build).
Run: pyinstaller ScreenAutomator.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Project root (SPECPATH is already the directory containing this .spec file)
PROJECT_DIR = os.path.abspath(SPECPATH)

# Collect data directories
datas = []
config_dir = os.path.join(PROJECT_DIR, 'config')
templates_dir = os.path.join(PROJECT_DIR, 'templates')
if os.path.isdir(config_dir):
    datas.append((config_dir, 'config'))
if os.path.isdir(templates_dir):
    datas.append((templates_dir, 'templates'))

# Collect PyQt6 data files
datas += collect_data_files('PyQt6', subdir='Qt6')

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtWidgets',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'cv2',
    'numpy',
    'PIL',
    'pyautogui',
    'pytesseract',
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'pynput.mouse',
    'pynput.mouse._win32',
] + collect_submodules('pynput')

a = Analysis(
    [os.path.join(PROJECT_DIR, 'main.py')],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ScreenAutomator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScreenAutomator',
)
