"""설정 창 테스트: 배치 계산, 숫자 입력칸 동작."""

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication

from piko.core.settings_schema import FieldKind, SettingField
from piko.ui.settings_dialog import NumberField, ToggleSwitch, place_near

MINUTES = SettingField(
    "m", "분", FieldKind.FLOAT, minimum=0.5, maximum=60, step=1, decimals=1, suffix=" 분"
)
SCALE = SettingField("s", "배율", FieldKind.INT, minimum=1, maximum=8, suffix=" 배")


def test_number_field_step_and_clamp(qt_app: QApplication) -> None:
    field = NumberField(MINUTES)
    field.setValue(30)
    assert field.edit.text() == "30"
    field._step(1)
    assert field.value() == 31
    field.setValue(0.1)  # 최솟값 아래
    assert field.value() == 0.5 and field.edit.text() == "0.5"
    field._step(-1)
    assert field.value() == 0.5
    field.setValue(99)
    assert field.value() == 60


def test_number_field_reads_typed_text_and_rejects_garbage(qt_app: QApplication) -> None:
    field = NumberField(SCALE)
    field.setValue(3)
    field.edit.setText("5")
    assert field.value() == 5
    field.edit.setText("")
    assert field.value() == 5  # 빈칸이면 이전 값


def test_toggle_switch(qt_app: QApplication) -> None:
    toggle = ToggleSwitch()
    assert not toggle.isChecked()
    toggle.click()
    assert toggle.isChecked()


SCREEN = QRect(0, 0, 1920, 1032)
SIZE = QSize(260, 300)


def test_left_of_widget_bottom_aligned() -> None:
    widget = QRect(1386, 728, 518, 288)
    assert place_near(widget, SIZE, SCREEN, gap=8) == QPoint(1386 - 8 - 260, 728 + 288 - 300)


def test_right_side_when_no_room_on_left() -> None:
    widget = QRect(100, 600, 518, 288)
    assert place_near(widget, SIZE, SCREEN, gap=8) == QPoint(100 + 518 + 8, 588)


def test_clamped_into_screen() -> None:
    widget = QRect(1300, 0, 518, 100)  # 위쪽 끝, 아래 맞추면 화면 위로 넘친다
    assert place_near(widget, SIZE, SCREEN, gap=8).y() == 0
