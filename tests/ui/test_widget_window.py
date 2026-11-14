"""위젯 창 위치 계산 테스트(Qt 앱 없이 동작)."""

from PySide6.QtCore import QPoint, QRect, QSize

from piko.ui.widget_window import bottom_right_position, clamp_into, is_visible_enough

PRIMARY = QRect(0, 0, 1920, 1040)
LEFT_MONITOR = QRect(-1280, 40, 1280, 984)


def test_bottom_right_position_with_margin() -> None:
    result = bottom_right_position(PRIMARY, QSize(160, 160), 16)
    assert result == QPoint(1920 - 160 - 16, 1040 - 160 - 16)


def test_bottom_right_position_respects_offset_origin() -> None:
    # 보조 모니터나 왼쪽/위 작업표시줄처럼 작업 영역 원점이 0이 아닌 경우
    result = bottom_right_position(LEFT_MONITOR, QSize(100, 50), 10)
    assert result == QPoint(-1280 + 1280 - 100 - 10, 40 + 984 - 50 - 10)


def test_visible_enough_inside_and_on_second_monitor() -> None:
    size = QSize(576, 360)
    assert is_visible_enough(QRect(QPoint(100, 100), size), [PRIMARY], 48)
    assert is_visible_enough(QRect(QPoint(-1000, 200), size), [PRIMARY, LEFT_MONITOR], 48)


def test_not_visible_when_monitor_is_gone() -> None:
    # 보조 모니터를 뺀 뒤 그 위치가 저장되어 있는 경우
    assert not is_visible_enough(QRect(QPoint(-1000, 200), QSize(576, 360)), [PRIMARY], 48)


def test_barely_visible_edge_is_rejected() -> None:
    rect = QRect(QPoint(1920 - 20, 500), QSize(576, 360))  # 20px만 걸침
    assert not is_visible_enough(rect, [PRIMARY], 48)
    assert is_visible_enough(rect.translated(-40, 0), [PRIMARY], 48)


def test_clamp_into_moves_inside() -> None:
    size = QSize(576, 360)
    assert clamp_into(QRect(QPoint(1800, 900), size), PRIMARY) == QPoint(1920 - 576, 1040 - 360)
    assert clamp_into(QRect(QPoint(-50, -10), size), PRIMARY) == QPoint(0, 0)
    assert clamp_into(QRect(QPoint(300, 200), size), PRIMARY) == QPoint(300, 200)


def test_clamp_into_larger_than_area_aligns_top_left() -> None:
    assert clamp_into(QRect(QPoint(500, 500), QSize(3000, 2000)), PRIMARY) == QPoint(0, 0)
