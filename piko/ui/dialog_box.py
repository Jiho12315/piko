"""방 장면 아래에 붙는 대화창 영역. 평소에는 비어 있고, 알림이 올 때만 문구와 버튼을 보인다."""

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from piko.core.ui_bus import DialogButton
from piko.ui import theme

# 크기는 원본 픽셀 기준(화면에는 배율을 곱한다). 고해상 도트(×1) 기준
DIALOG_HEIGHT = 56
BORDER_WIDTH = theme.BORDER_WIDTH
PADDING = 8
BUTTON_SPACING = 8


class DialogBox(QWidget):
    """문구 한 줄과 버튼 몇 개를 보여 준다. 버튼은 포커스를 받지 않는다."""

    button_clicked = Signal(str)

    def __init__(self, width: int, scale: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = scale
        self.setFixedSize(width * scale, DIALOG_HEIGHT * scale)
        self.setFont(theme.ui_font(theme.FONT_SIZE * scale))

        margin = (BORDER_WIDTH + PADDING) * scale
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(BUTTON_SPACING * scale)
        self._label = QLabel(self)
        self._label.setFont(theme.ui_font(theme.FONT_SIZE_LARGE * scale))  # 알림 문구는 크게
        self._label.setStyleSheet(theme.label_style())
        self._layout.addWidget(self._label, stretch=1)
        self._buttons: list[QPushButton] = []

    @property
    def text(self) -> str:
        """지금 보이는 문구(없으면 빈 문자열)."""
        return self._label.text()

    @property
    def button_ids(self) -> list[str]:
        """지금 보이는 버튼 id 목록."""
        return [str(button.property("button_id")) for button in self._buttons]

    def show_message(self, text: str, buttons: Sequence[DialogButton] = ()) -> None:
        """문구와 버튼을 보여 준다. 이전 버튼은 지운다."""
        self._clear_buttons()
        self._label.setText(text)
        style = theme.button_style(BORDER_WIDTH * self._scale, PADDING * self._scale)
        for spec in buttons:
            button = QPushButton(spec.label, self)
            button.setProperty("button_id", spec.id)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(style)
            button.clicked.connect(lambda _=False, bid=spec.id: self.button_clicked.emit(bid))
            self._layout.addWidget(button)
            self._buttons.append(button)
            if self.isVisible():
                button.show()  # 보이는 위젯에 새로 넣은 자식은 Qt가 늦게 표시한다
        self._layout.activate()

    def clear(self) -> None:
        """문구와 버튼을 모두 지운다."""
        self._label.clear()
        self._clear_buttons()

    def _clear_buttons(self) -> None:
        for button in self._buttons:
            self._layout.removeWidget(button)
            button.deleteLater()
        self._buttons.clear()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt 재정의)
        """테두리와 바탕을 그린다."""
        theme.paint_frame(QPainter(self), self.rect(), BORDER_WIDTH * self._scale)
