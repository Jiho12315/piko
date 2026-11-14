"""app 보조 함수 테스트."""

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication

from piko.app import SettingsController, saved_position
from piko.core.attention import AttentionCoordinator
from piko.core.config import ConfigStore
from piko.core.feature_base import FeatureContext, FeatureRegistry
from piko.core.ui_bus import UiBus


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"x": 10, "y": -20}, QPoint(10, -20)),
        ({"x": None, "y": None}, None),
        ({}, None),
        ({"x": 10, "y": None}, None),
        ({"x": "10", "y": 5}, None),
        ({"x": True, "y": 5}, None),
    ],
)
def test_saved_position(values: dict[str, Any], expected: QPoint | None) -> None:
    assert saved_position(values) == expected


class _FakeWindow:
    def frameGeometry(self) -> QRect:  # noqa: N802 (Qt 이름 흉내)
        return QRect(1000, 600, 518, 288)


class _FakeView:
    scale = 1


def _controller(tmp_path: Path) -> SettingsController:
    config = ConfigStore(tmp_path / "config.json")
    registry = FeatureRegistry(config, FeatureContext(UiBus(), AttentionCoordinator()))
    return SettingsController(config, registry, _FakeWindow(), _FakeView())  # type: ignore[arg-type]


def test_settings_dialog_is_modeless(tmp_path: Path) -> None:
    # 설정 창이 열려 있어도 위젯(타이머 패널 등)을 쓸 수 있어야 한다
    controller = _controller(tmp_path)
    controller.open()
    dialog = controller._dialog
    assert dialog is not None and dialog.isVisible()
    assert not dialog.isModal()
    assert QApplication.activeModalWidget() is None
    controller.open()  # 다시 열면 같은 창
    assert controller._dialog is dialog
    dialog.reject()
    assert controller._dialog is None
    controller.open()  # 닫은 뒤에는 새로 열린다
    assert controller._dialog is not None and controller._dialog is not dialog
    controller._dialog.reject()
