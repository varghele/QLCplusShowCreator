# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for QLC+ Show Creator (bundled with Visualizer)."""

import os

project_root = os.path.abspath(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('custom_fixtures', 'custom_fixtures'),
        ('resources', 'resources'),
        ('riffs', 'riffs'),
        ('visualizer', 'visualizer'),
    ],
    hiddenimports=[
        'visualizer',
        'visualizer.main',
        'visualizer.artnet',
        'visualizer.artnet.listener',
        'visualizer.renderer',
        'visualizer.renderer.camera',
        'visualizer.renderer.engine',
        'visualizer.renderer.fixtures',
        'visualizer.renderer.gizmo',
        'visualizer.renderer.stage',
        'visualizer.tcp',
        'visualizer.tcp.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QLCShowCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(project_root, 'resources', 'lightbulb.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QLCShowCreator',
)
