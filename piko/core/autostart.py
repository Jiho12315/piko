"""윈도우 시작 시 자동 실행: 시작 프로그램 폴더에 Piko.lnk 바로가기를 둔다.

스마트 앱 컨트롤이 서명 없는 exe를 막으므로 서명된 pythonw.exe로 main.py를 실행한다.
예전 버전이 쓰던 레지스트리 Run 키 등록은 발견하면 바로가기로 옮기고 지운다.
"""

import logging
import os
import sys
import winreg
from pathlib import Path

from piko.core import paths, shortcut
from piko.core.shortcut import Shortcut

SHORTCUT_NAME = "Piko.lnk"
DESCRIPTION = "피코 데스크탑 마스코트"
STARTUP_PARTS = ("Microsoft", "Windows", "Start Menu", "Programs", "Startup")
PYTHONW_NAME = "pythonw.exe"
LEGACY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LEGACY_VALUE_NAME = "Piko"

logger = logging.getLogger(__name__)


def startup_dir() -> Path:
    """사용자 시작 프로그램 폴더(shell:startup)."""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return root.joinpath(*STARTUP_PARTS)


def launch_shortcut() -> Shortcut:
    """지금 실행 중인 피코를 다시 실행하는 바로가기 내용.

    소스 실행이면 콘솔 없는 pythonw.exe + main.py, exe로 묶였으면 그 exe.
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        return Shortcut(exe, working_dir=exe.parent, icon=exe, description=DESCRIPTION)
    script = paths.entry_script()
    return Shortcut(
        Path(sys.executable).with_name(PYTHONW_NAME),
        arguments=f'"{script}"',
        working_dir=script.parent,
        icon=paths.app_icon_path(),
        description=DESCRIPTION,
    )


def _link(folder: Path | None) -> Path:
    return (folder or startup_dir()) / SHORTCUT_NAME


def is_enabled(folder: Path | None = None) -> bool:
    """자동 실행 바로가기가 있는지."""
    return _link(folder).exists()


def enable(link: Shortcut, folder: Path | None = None) -> None:
    """시작 프로그램 폴더에 바로가기를 만든다(있으면 덮어쓴다). 실패하면 OSError."""
    shortcut.create(_link(folder), link)
    logger.info("자동 실행 등록: %s", _link(folder))


def disable(folder: Path | None = None) -> None:
    """바로가기를 지운다. 없으면 아무것도 하지 않는다. 실패하면 OSError."""
    _link(folder).unlink(missing_ok=True)
    logger.info("자동 실행 해제")


def refresh_if_moved(link: Shortcut, folder: Path | None = None) -> bool:
    """등록된 바로가기의 실행 파일이나 스크립트가 없어졌으면 지금 내용으로 다시 만든다.

    파일이 그대로 있으면 다른 위치에서 실행해도 건드리지 않는다. 고쳤으면 True.
    """
    if not is_enabled(folder):
        return False
    target, arguments = shortcut.read(_link(folder))
    if all(path.exists() for path in (target, *shortcut.quoted_paths(arguments))):
        return False
    logger.info("등록된 실행 파일이 없어 자동 실행 바로가기를 고칩니다: %s %s", target, arguments)
    enable(link, folder)
    return True


def migrate_legacy(
    link: Shortcut, folder: Path | None = None, key_path: str = LEGACY_RUN_KEY
) -> bool:
    """예전 레지스트리 Run 등록이 있으면 바로가기로 옮기고 지운다. 옮겼으면 True."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
        ) as key:
            winreg.QueryValueEx(key, LEGACY_VALUE_NAME)
            enable(link, folder)
            winreg.DeleteValue(key, LEGACY_VALUE_NAME)
    except FileNotFoundError:
        return False
    logger.info("레지스트리 자동 실행 등록을 바로가기로 옮겼습니다")
    return True
