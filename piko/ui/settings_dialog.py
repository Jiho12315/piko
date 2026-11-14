"""설정 창. 설정 스키마(SettingsSection) 목록을 보고 입력칸을 만든다.

위젯 테마(베이지 바탕, 각진 갈색 테두리, 도트 글꼴)로 직접 그린 테두리 없는 팝업이다.
제목 부분을 끌어서 옮길 수 있고, 위젯 근처에 뜬다.
"""

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QLocale, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QDoubleValidator, QGuiApplication, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from piko.core.settings_schema import FieldKind, SettingField, SettingsSection, normalize_value
from piko.ui import theme

TEXT_TITLE = "설정"
TEXT_SAVE = "저장"
TEXT_CANCEL = "취소"
TEXT_CLOSE = "X"
TEXT_MINUS = "−"
TEXT_PLUS = "+"

PADDING = 12
SECTION_SPACING = 10
ROW_SPACING = 6
LABEL_GAP = 16
STEP_BUTTON_SIZE = 20
INPUT_WIDTH = 48
UNIT_WIDTH = 16
TOGGLE_SIZE = QSize(36, 18)
TOGGLE_KNOB_INSET = 3
DIVIDER_HEIGHT = 2
SCREEN_GAP = 8  # 위젯과 설정 창 사이 간격


class NumberField(QWidget):
    """[−][입력칸][+] 단위. 버튼은 SettingField.step만큼 바꾸고, 값은 범위 안으로 자른다.

    (스타일을 입힌 QSpinBox는 숨긴 화살표 자리 때문에 글자 영역이 1px로 줄어 일반 입력칸을 쓴다)
    """

    def __init__(self, field: SettingField, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._field = field
        self._value: float = field.minimum
        self.edit = QLineEdit(self)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit.setFixedWidth(INPUT_WIDTH)
        self.edit.setStyleSheet(theme.input_style())
        decimals = field.decimals if field.kind == FieldKind.FLOAT else 0
        validator = QDoubleValidator(field.minimum, field.maximum, decimals, self.edit)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        validator.setLocale(QLocale.c())  # 소수점은 항상 '.'
        self.edit.setValidator(validator)
        self.edit.editingFinished.connect(self._commit_text)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for text, direction in ((TEXT_MINUS, -1), (TEXT_PLUS, 1)):
            button = QPushButton(text, self)
            button.setFixedSize(STEP_BUTTON_SIZE, STEP_BUTTON_SIZE)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme.button_style(padding=0))
            button.clicked.connect(lambda _=False, d=direction: self._step(d))
            layout.addWidget(button)
            if direction < 0:
                layout.addWidget(self.edit)
        unit = QLabel(field.suffix.strip(), self)
        unit.setStyleSheet(theme.label_style())
        unit.setFixedWidth(UNIT_WIDTH)
        layout.addWidget(unit)

    def value(self) -> float:
        """입력값(입력 중인 글자도 반영)."""
        self._commit_text()
        return self._value

    def setValue(self, value: float) -> None:  # noqa: N802 (Qt 입력칸과 같은 이름)
        """입력값을 바꾼다(범위 안으로 자른다)."""
        self._value = float(normalize_value(self._field, value))
        self.edit.setText(_format_number(normalize_value(self._field, value)))

    def _step(self, direction: int) -> None:
        self.setValue(self.value() + direction * self._field.step)

    def _commit_text(self) -> None:
        text = self.edit.text().strip()
        try:
            self.setValue(float(text))
        except ValueError:
            self.setValue(self._value)  # 잘못된 입력은 이전 값으로


def _format_number(value: float) -> str:
    """30 → "30", 0.5 → "0.5"."""
    return f"{value:g}"


class ToggleSwitch(QAbstractButton):
    """각진 도트 토글. 켜지면 노란 바탕에 칸이 오른쪽으로 간다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(TOGGLE_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:  # noqa: N802
        """고정 크기."""
        return TOGGLE_SIZE

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """테두리, 바탕, 손잡이 칸을 그린다."""
        painter = QPainter(self)
        border = theme.POPUP_BORDER_WIDTH
        rect = self.rect()
        painter.fillRect(rect, theme.BORDER_COLOR)
        track = theme.TOGGLE_ON_COLOR if self.isChecked() else theme.TOGGLE_OFF_COLOR
        painter.fillRect(rect.adjusted(border, border, -border, -border), track)
        knob = rect.height() - 2 * TOGGLE_KNOB_INSET
        x = rect.width() - TOGGLE_KNOB_INSET - knob if self.isChecked() else TOGGLE_KNOB_INSET
        knob_rect = QRect(x, TOGGLE_KNOB_INSET, knob, knob)
        painter.fillRect(knob_rect, theme.BORDER_COLOR)
        painter.fillRect(knob_rect.adjusted(1, 1, -1, -1), theme.INPUT_COLOR)


class TitleBar(QWidget):
    """제목과 닫기 버튼. 잡고 끌면 창이 따라 움직인다."""

    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_offset: QPoint | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(TEXT_TITLE, self)
        title.setFont(theme.ui_font(bold=True))
        title.setStyleSheet(theme.label_style())
        close = QPushButton(TEXT_CLOSE, self)
        close.setObjectName("close")
        close.setFixedSize(STEP_BUTTON_SIZE, STEP_BUTTON_SIZE)
        close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(theme.button_style(padding=0))
        close.clicked.connect(dialog.reject)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(close)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """끌기 시작."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._dialog.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """끄는 동안 창을 옮긴다."""
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """끌기 끝."""
        self._drag_offset = None


def _divider(parent: QWidget) -> QFrame:
    line = QFrame(parent)
    line.setFixedHeight(DIVIDER_HEIGHT)
    line.setStyleSheet(f"background: {theme.DIVIDER_COLOR.name()}; border: none;")
    return line


def _make_editor(field: SettingField, value: Any, parent: QWidget) -> QWidget:
    if field.kind == FieldKind.BOOL:
        toggle = ToggleSwitch(parent)
        toggle.setChecked(bool(value))
        return toggle
    number = NumberField(field, parent)
    number.setValue(normalize_value(field, value))
    return number


def _read_editor(field: SettingField, editor: QWidget) -> Any:
    if isinstance(editor, ToggleSwitch):
        return normalize_value(field, editor.isChecked())
    assert isinstance(editor, NumberField)
    return normalize_value(field, editor.value())


def place_near(anchor: QRect, size: QSize, area: QRect, gap: int = SCREEN_GAP) -> QPoint:
    """anchor(위젯) 왼쪽에 아래쪽을 맞춰 놓는다.

    왼쪽에 자리가 없으면 오른쪽에 두고, 그래도 넘치면 화면 안으로 민다.
    """
    x = anchor.x() - gap - size.width()
    if x < area.x():
        x = anchor.x() + anchor.width() + gap
    y = anchor.y() + anchor.height() - size.height()
    x = max(area.x(), min(x, area.x() + area.width() - size.width()))
    y = max(area.y(), min(y, area.y() + area.height() - size.height()))
    return QPoint(x, y)


class SettingsDialog(QDialog):
    """섹션별로 항목을 나열하고, [저장]을 누르면 values()로 결과를 준다."""

    def __init__(
        self,
        sections: Sequence[tuple[SettingsSection, dict[str, Any]]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TEXT_TITLE)
        # 위젯 창이 항상 맨 위라서 설정 창도 맨 위에 둬야 가려지지 않는다
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFont(theme.ui_font())
        self._editors: list[tuple[str, SettingField, QWidget]] = []

        border = theme.POPUP_BORDER_WIDTH
        margin = border + PADDING
        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(SECTION_SPACING)
        layout.addWidget(TitleBar(self))
        for section, values in sections:
            layout.addWidget(_divider(self))
            heading = QLabel(section.title, self)
            heading.setFont(theme.ui_font(bold=True))
            heading.setStyleSheet(theme.label_style())
            layout.addWidget(heading)
            grid = QGridLayout()
            grid.setHorizontalSpacing(LABEL_GAP)
            grid.setVerticalSpacing(ROW_SPACING)
            grid.setColumnStretch(0, 1)
            for row, field in enumerate(section.fields):
                label = QLabel(field.label, self)
                label.setStyleSheet(theme.label_style())
                editor = _make_editor(field, values.get(field.key), self)
                editor.setObjectName(f"{section.name}.{field.key}")
                grid.addWidget(label, row, 0)
                grid.addWidget(editor, row, 1, alignment=Qt.AlignmentFlag.AlignRight)
                self._editors.append((section.name, field, editor))
            layout.addLayout(grid)
        layout.addWidget(_divider(self))

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for text, slot, name in (
            (TEXT_SAVE, self.accept, "save"),
            (TEXT_CANCEL, self.reject, "cancel"),
        ):
            button = QPushButton(text, self)
            button.setObjectName(name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme.button_style())
            button.clicked.connect(slot)
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def place_near(self, anchor: QRect) -> None:
        """위젯(anchor) 근처, 화면 안에 놓는다."""
        self.adjustSize()
        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        self.move(place_near(anchor, self.size(), screen.availableGeometry()))

    def editor(self, section: str, key: str) -> QWidget:
        """입력칸을 찾는다(테스트·자동 확인용)."""
        return next(e for s, f, e in self._editors if s == section and f.key == key)

    def values(self) -> dict[str, dict[str, Any]]:
        """섹션별 입력값. 종류와 범위에 맞게 정리된 값이다."""
        result: dict[str, dict[str, Any]] = {}
        for section, field, editor in self._editors:
            result.setdefault(section, {})[field.key] = _read_editor(field, editor)
        return result

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """각진 갈색 2px 테두리와 베이지 바탕."""
        theme.paint_frame(QPainter(self), self.rect(), theme.POPUP_BORDER_WIDTH)
