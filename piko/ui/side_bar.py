"""방 오른쪽의 세로 아이콘 메뉴바. 항목 목록(SideBarItem)을 넘기면 위에서부터 버튼을 만든다."""

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPaintEvent
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from piko.ui import theme
from piko.ui.pixel_icons import ICON_SIZE, icon_pixmap

ICON_SCALE = 2  # 16px 아이콘을 2배(32px)로
BUTTON_PADDING = 4
BAR_PADDING = 4
BAR_WIDTH = ICON_SIZE * ICON_SCALE + 2 * (BUTTON_PADDING + BAR_PADDING + theme.BORDER_WIDTH)


@dataclass(frozen=True)
class SideBarItem:
    """메뉴바 항목. 아이콘은 id로 찾는다(pixel_icons). checkable이면 눌린 상태가 유지된다."""

    id: str
    tooltip: str
    checkable: bool = False


class SideBar(QWidget):
    """세로 아이콘 버튼 묶음. 눌리면 item_clicked(id)를 보낸다. 포커스를 받지 않는다."""

    item_clicked = Signal(str)

    def __init__(self, items: Sequence[SideBarItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(BAR_WIDTH)
        margin = theme.BORDER_WIDTH + BAR_PADDING
        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(BAR_PADDING)
        style = theme.tool_button_style(BUTTON_PADDING)
        icon_px = ICON_SIZE * ICON_SCALE
        self._buttons: dict[str, QToolButton] = {}
        for item in items:
            button = QToolButton(self)
            button.setIcon(QIcon(icon_pixmap(item.id, icon_px)))
            button.setIconSize(QSize(icon_px, icon_px))
            button.setToolTip(item.tooltip)
            button.setCheckable(item.checkable)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(style)
            button.clicked.connect(lambda _=False, item_id=item.id: self.item_clicked.emit(item_id))
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._buttons[item.id] = button
        layout.addStretch(1)

    @property
    def item_ids(self) -> list[str]:
        """위에서부터 항목 id."""
        return list(self._buttons)

    def button(self, item_id: str) -> QToolButton:
        """항목 버튼."""
        return self._buttons[item_id]

    def set_checked(self, item_id: str, checked: bool) -> None:
        """눌린 상태 표시를 실제 상태에 맞춘다."""
        self._buttons[item_id].setChecked(checked)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt 재정의)
        """테두리와 바탕을 그린다."""
        theme.paint_frame(QPainter(self), self.rect())
