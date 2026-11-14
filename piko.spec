# PyInstaller 빌드 설정. 사용법: .\.venv\Scripts\pyinstaller.exe piko.spec --noconfirm
# 결과: dist\Piko.exe (단일 exe, 콘솔 창 없음, assets 포함)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets")],  # paths.asset_path()가 _MEIPASS/assets에서 찾는다
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 쓰지 않는 큰 모듈은 빼서 exe 크기를 줄인다
    excludes=["tkinter", "unittest", "pydoc", "pytest", "PyInstaller"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Piko",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon="assets/ui/piko.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
