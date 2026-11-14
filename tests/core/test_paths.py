"""paths 모듈 테스트."""

from pathlib import Path

import pytest

from piko.core import paths


def test_app_data_dir_uses_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    result = paths.app_data_dir()
    assert result == tmp_path / paths.APP_DIR_NAME
    assert result.is_dir()


def test_logs_dir_and_config_path_under_app_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app_dir = tmp_path / paths.APP_DIR_NAME
    assert paths.logs_dir() == app_dir / paths.LOGS_DIR_NAME
    assert paths.logs_dir().is_dir()
    assert paths.config_path() == app_dir / paths.CONFIG_FILE_NAME


def test_asset_path_points_into_project_assets() -> None:
    result = paths.asset_path("idle")
    assert result == paths.project_root() / paths.ASSETS_DIR_NAME / "idle"
    assert (paths.project_root() / "pyproject.toml").is_file()
