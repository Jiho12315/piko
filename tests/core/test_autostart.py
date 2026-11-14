"""자동 실행(시작 프로그램 폴더 바로가기) 테스트.

실제 시작 프로그램 폴더 대신 tmp_path를, 실제 Run 키 대신 테스트 전용 키를 쓴다.
바로가기는 실제로 PowerShell로 만들고 읽는다.
"""

import sys
import uuid
import winreg
from collections.abc import Iterator
from pathlib import Path

import pytest

from piko.core import autostart, paths, shortcut
from piko.core.shortcut import Shortcut


@pytest.fixture
def key_path() -> Iterator[str]:
    path = rf"Software\PikoTest\{uuid.uuid4().hex}"
    yield path
    for sub in (path, r"Software\PikoTest"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except OSError:
            pass


def _fake_program(folder: Path) -> Shortcut:
    """존재하는 실행 파일·스크립트로 된 바로가기 내용(한글·공백 경로)."""
    folder.mkdir(parents=True, exist_ok=True)
    exe = folder / "pythonw.exe"
    script = folder / "main.py"
    exe.write_bytes(b"")
    script.write_text("")
    return Shortcut(exe, f'"{script}"', working_dir=folder, description="테스트")


def test_create_and_read_shortcut(tmp_path: Path) -> None:
    link = _fake_program(tmp_path / "바탕 화면")
    path = tmp_path / "Piko.lnk"
    shortcut.create(path, link)
    assert shortcut.read(path) == (link.target, link.arguments)


def test_enable_disable_roundtrip(tmp_path: Path) -> None:
    startup = tmp_path / "Startup"
    assert not autostart.is_enabled(startup)
    autostart.enable(_fake_program(tmp_path / "app"), startup)
    assert autostart.is_enabled(startup)
    assert (startup / autostart.SHORTCUT_NAME).exists()
    autostart.disable(startup)
    assert not autostart.is_enabled(startup)
    autostart.disable(startup)  # 없을 때 지워도 괜찮다


def test_refresh_does_nothing_when_not_enabled(tmp_path: Path) -> None:
    assert autostart.refresh_if_moved(_fake_program(tmp_path / "app"), tmp_path) is False
    assert not autostart.is_enabled(tmp_path)


def test_refresh_keeps_existing_target(tmp_path: Path) -> None:
    installed = _fake_program(tmp_path / "설치")
    autostart.enable(installed, tmp_path)
    other = _fake_program(tmp_path / "dev")
    assert autostart.refresh_if_moved(other, tmp_path) is False
    assert shortcut.read(tmp_path / autostart.SHORTCUT_NAME)[0] == installed.target


def test_refresh_when_script_is_gone(tmp_path: Path) -> None:
    old = _fake_program(tmp_path / "old")
    autostart.enable(old, tmp_path)
    (tmp_path / "old" / "main.py").unlink()  # 프로젝트 폴더를 옮긴 경우
    new = _fake_program(tmp_path / "new")
    assert autostart.refresh_if_moved(new, tmp_path) is True
    assert shortcut.read(tmp_path / autostart.SHORTCUT_NAME)[0] == new.target


def test_migrate_legacy_registry(tmp_path: Path, key_path: str) -> None:
    link = _fake_program(tmp_path / "app")
    assert autostart.migrate_legacy(link, tmp_path, key_path) is False
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, autostart.LEGACY_VALUE_NAME, 0, winreg.REG_SZ, r'"C:\x\Piko.exe"')
    assert autostart.migrate_legacy(link, tmp_path, key_path) is True
    assert autostart.is_enabled(tmp_path)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        with pytest.raises(FileNotFoundError):
            winreg.QueryValueEx(key, autostart.LEGACY_VALUE_NAME)


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ('"C:\\a b\\main.py"', [Path("C:\\a b\\main.py")]),
        ('"C:\\x\\main.py" --flag', [Path("C:\\x\\main.py")]),
        ("", []),
    ],
)
def test_quoted_paths(arguments: str, expected: list[Path]) -> None:
    assert shortcut.quoted_paths(arguments) == expected


def test_launch_shortcut_from_source_uses_pythonw() -> None:
    link = autostart.launch_shortcut()
    assert link.target.name == "pythonw.exe"
    assert link.arguments == f'"{paths.entry_script()}"'
    assert link.icon == paths.app_icon_path()


def test_launch_shortcut_when_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\Piko.exe")
    link = autostart.launch_shortcut()
    assert link.target == Path(r"C:\Apps\Piko.exe") and link.arguments == ""


def test_startup_dir_under_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert autostart.startup_dir() == tmp_path.joinpath(*autostart.STARTUP_PARTS)


def test_app_icon_exists() -> None:
    assert paths.app_icon_path().exists()
