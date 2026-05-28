# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ShoeBillingApp v1.1.2
打包命令: pyinstaller --clean ShoeBillingApp.spec
"""

import os
import sys
import shutil
from pathlib import Path

block_cipher = None

# 获取源文件所在目录
src_dir = r"D:\鞋类开单报价系统（版本管理）\鞋类产品报价开单系统v1.1.2"

# 收集需要包含的数据文件（ShoeBilling_Data 目录下的 .ico 图标等）
# 如果有自定义图标或资源文件，在这里添加
datas = []

# 检查是否有 app.ico 或图标文件
for icon_file in ["app.ico", "app.png", "app.jpg"]:
    icon_path = os.path.join(src_dir, icon_file)
    if os.path.exists(icon_path):
        datas.append((icon_path, "."))
        print(f"添加图标: {icon_path}")
        break

# 收集 .json 数据文件作为数据源（运行时读取）
# 注意：这些是程序运行时读取的配置/数据文件，不应打包进 exe
# 用户数据在 ShoolBilling_Data 目录中，运行时自动创建
# 不需要额外 datas 条目

a = Analysis(
    [os.path.join(src_dir, "ShoeBillingApp.py")],
    pathex=[src_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageGrab",
        "tkinter",
        "base64",
        "json",
        "os",
        "sys",
        "webbrowser",
        "datetime",
        "uuid",
        "hashlib",
        "subprocess",
        "shutil",
        "csv",
        "io",
        "ctypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.ttk", "test", "unittest", "email", "xml", "numpy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="鞋类产品报价开单系统v1.1.2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标，设为 icon 路径
)
