"""리소스(assets)와 사용자 데이터(APPDATA) 경로를 한곳에서 관리한다."""

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Piko"
ASSETS_DIR_NAME = "assets"
LOGS_DIR_NAME = "logs"
CONFIG_FILE_NAME = "config.json"
APP_ICON_PARTS = ("ui", "piko.ico")  # tools/make_icon.py가 만든다
ENTRY_SCRIPT = "main.py"


def project_root() -> Path:
    """소스 루트를 반환한다. PyInstaller로 묶인 경우 압축 해제 폴더를 반환한다."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir is not None:
        return Path(bundle_dir)
    return Path(__file__).resolve().parents[2]


def asset_path(*parts: str) -> Path:
    """assets 폴더 아래 경로를 반환한다. 예: asset_path("idle")."""
    return project_root().joinpath(ASSETS_DIR_NAME, *parts)


def app_icon_path() -> Path:
    """피코 아이콘(.ico) 경로. 트레이와 바로가기에 쓴다."""
    return asset_path(*APP_ICON_PARTS)


def entry_script() -> Path:
    """소스 실행 진입점(main.py) 경로."""
    return Path(__file__).resolve().parents[2] / ENTRY_SCRIPT


def app_data_dir() -> Path:
    """%APPDATA%/Piko 폴더를 반환한다(없으면 만든다)."""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    path = root / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    """로그 폴더를 반환한다(없으면 만든다)."""
    path = app_data_dir() / LOGS_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    """설정 파일 경로를 반환한다."""
    return app_data_dir() / CONFIG_FILE_NAME
