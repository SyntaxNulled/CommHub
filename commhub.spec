# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CommHub — local-first communication hub."""

import sys
from pathlib import Path

block_cipher = None

datas = [
    (str(Path("app/static")), "app/static"),
]

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "aiosqlite",
    "apscheduler",
    "apscheduler.triggers.cron",
    "apscheduler.executors.asyncio",
    "pydantic",
    "pydantic_settings",
    "jinja2",
    "aiofiles",
    "multipart",
    "httpx",
    "openai",
    "anthropic",
    "pystray",
    "PIL",
    "PIL.Image",
]

excludes = [
    "tkinter",
    "unittest",
    "test",
    "distutils",
    "setuptools",
    "pip",
    "Cython",
    "numpy",
    "matplotlib",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_no_redirects=False,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="commhub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico" if Path("app.ico").exists() else None,
)
