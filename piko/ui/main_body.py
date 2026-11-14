"""위젯 창 본체: [방 장면 + 대화창] [세로 메뉴바] [타이머 패널(펼쳤을 때만)]을 가로로 붙인다."""

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QHBoxLayout, QLayout, QWidget

from piko.ui.piko_view import PikoView
from piko.ui.side_bar import SideBar
from piko.ui.timer_panel import TimerPanel
from piko.ui.widget_window import WidgetWindow


class MainBody(QWidget):
    """메뉴바와 패널은 방 영역 높이에 맞춰 늘어난다. 패널을 펼치면 오른쪽으로 넓어진다."""

    def __init__(
        self,
        view: PikoView,
        side_bar: SideBar,
        panel: TimerPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.view = view
        self.side_bar = side_bar
        self.panel = panel
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.addWidget(view)
        layout.addWidget(side_bar)
        layout.addWidget(panel)
        panel.hide()
        self._layout = layout

    @property
    def panel_visible(self) -> bool:
        """패널이 펼쳐져 있는지."""
        return not self.panel.isHidden()

    def set_panel_visible(self, visible: bool) -> None:
        """패널을 펼치거나 접고 크기를 바로 다시 계산한다."""
        self.panel.setVisible(visible)
        self._layout.activate()


class PanelToggler:
    """타이머 패널을 펼치고 접으면서 창 위치를 맞춘다.

    펼칠 때 화면 오른쪽 끝을 넘으면 창을 왼쪽으로 밀고, 접을 때 원래 자리로 돌려놓는다.
    그 사이에 사용자가 창을 옮겼으면 돌려놓지 않는다.
    """

    def __init__(self, window: WidgetWindow, body: MainBody, toggle_item_id: str) -> None:
        self._window = window
        self._body = body
        self._item_id = toggle_item_id
        self._restore_to: QPoint | None = None

    def toggle(self) -> None:
        """펼쳐져 있으면 접고, 접혀 있으면 펼친다."""
        self.set_open(not self._body.panel_visible)

    def set_open(self, opened: bool) -> None:
        """패널을 펼치거나 접는다."""
        before = self._window.pos()
        position = self._window.refit_in_screen(lambda: self._body.set_panel_visible(opened))
        if opened:
            self._restore_to = before if position != before else None
        elif self._restore_to is not None:
            self._window.move(self._restore_to)
            self._restore_to = None
        self._body.side_bar.set_checked(self._item_id, opened)

    def forget_restore(self) -> None:
        """사용자가 창을 옮겼으면 접을 때 되돌리지 않는다."""
        self._restore_to = None
