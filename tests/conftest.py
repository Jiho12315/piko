"""전체 테스트 공용: 창을 띄우지 않는 QApplication을 하나만 만든다.

QCoreApplication을 먼저 만들면 뒤의 위젯 테스트가 QWidget을 만들지 못하므로 여기서 통일한다.
"""

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402 (플랫폼 설정 뒤에 불러온다)


@pytest.fixture(scope="session", autouse=True)
def qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app
