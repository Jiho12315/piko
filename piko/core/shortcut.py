"""윈도우 바로가기(.lnk) 만들기·읽기.

새 라이브러리 없이 PowerShell의 WScript.Shell COM 객체를 쓴다. 경로는 환경 변수로 넘겨
따옴표·한글 문제를 피하고, 결과는 UTF-8로 받는다. 콘솔 창은 띄우지 않는다.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

POWERSHELL = "powershell.exe"
POWERSHELL_ARGS = ("-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command")
TIMEOUT_S = 20
ENV_PREFIX = "PIKO_LNK_"
WINDOW_STYLE_NORMAL = 1

_CREATE_SCRIPT = f"""
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:{ENV_PREFIX}PATH)
$s.TargetPath = $env:{ENV_PREFIX}TARGET
$s.Arguments = $env:{ENV_PREFIX}ARGS
$s.WorkingDirectory = $env:{ENV_PREFIX}WORKDIR
$s.IconLocation = $env:{ENV_PREFIX}ICON + ',0'
$s.Description = $env:{ENV_PREFIX}DESC
$s.WindowStyle = {WINDOW_STYLE_NORMAL}
$s.Save()
"""

_READ_SCRIPT = f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:{ENV_PREFIX}PATH)
[Console]::Out.Write($s.TargetPath + "`n" + $s.Arguments)
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Shortcut:
    """바로가기 내용. arguments는 명령줄 그대로(공백 있는 경로는 따옴표로 감싼다)."""

    target: Path
    arguments: str = ""
    working_dir: Path | None = None
    icon: Path | None = None
    description: str = ""


def _run(script: str, env: dict[str, str]) -> str:
    """PowerShell 스크립트를 콘솔 없이 실행하고 표준 출력을 돌려준다. 실패하면 OSError."""
    try:
        result = subprocess.run(
            [POWERSHELL, *POWERSHELL_ARGS, script],
            env={**os.environ, **env},
            capture_output=True,
            timeout=TIMEOUT_S,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError(f"PowerShell 응답 없음({TIMEOUT_S}초)") from exc
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(f"PowerShell 실패({result.returncode}): {error}")
    return result.stdout.decode("utf-8", errors="replace")


def create(path: Path, shortcut: Shortcut) -> None:
    """바로가기를 만든다(있으면 덮어쓴다). 실패하면 OSError."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        _CREATE_SCRIPT,
        {
            f"{ENV_PREFIX}PATH": str(path),
            f"{ENV_PREFIX}TARGET": str(shortcut.target),
            f"{ENV_PREFIX}ARGS": shortcut.arguments,
            f"{ENV_PREFIX}WORKDIR": str(shortcut.working_dir or ""),
            f"{ENV_PREFIX}ICON": str(shortcut.icon or shortcut.target),
            f"{ENV_PREFIX}DESC": shortcut.description,
        },
    )
    logger.info("바로가기 생성: %s → %s %s", path, shortcut.target, shortcut.arguments)


def read(path: Path) -> tuple[Path, str]:
    """바로가기의 (대상 경로, 인수)를 읽는다. 실패하면 OSError."""
    if not path.exists():
        raise FileNotFoundError(path)
    target, _, arguments = _run(_READ_SCRIPT, {f"{ENV_PREFIX}PATH": str(path)}).partition("\n")
    return Path(target), arguments


def quoted_paths(arguments: str) -> list[Path]:
    """인수 문자열에서 따옴표로 감싼 경로들을 꺼낸다. 예: '"C:\\a b\\x.py" -v' → [C:\\a b\\x.py]."""
    return [Path(part) for part in arguments.split('"')[1::2] if part]
