"""트레이 아이콘과 메뉴. 동작은 시그널로만 알리고 직접 처리하지 않는다."""

import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from piko.core import paths

logger = logging.getLogger(__name__)

TOOLTIP = "피코"
TEXT_SHOW = "보이기"
TEXT_HIDE = "숨기기"
TEXT_QUIT = "종료"
TEXT_SETTINGS = "설정…"
TEXT_AUTOSTART = "윈도우 시작 시 실행"

# 아이콘 파일(assets/ui/piko.ico)이 없을 때 쓰는 임시 아이콘(원)
ICON_SIZE = 64
ICON_COLOR = QColor(255, 160, 60)


def _make_icon() -> QIcon:
    """피코 아이콘. 파일이 없으면 단색 원."""
    icon = QIcon(str(paths.app_icon_path()))
    if not icon.isNull():
        return icon
    logger.warning("아이콘 파일이 없어 임시 아이콘을 씁니다: %s", paths.app_icon_path())
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ICON_COLOR)
    painter.drawEllipse(pixmap.rect())
    painter.end()
    return QIcon(pixmap)


class Tray(QObject):
    """트레이 아이콘. 메뉴: [보이기/숨기기] [설정…] [기능별 항목…] ─ [시작 시 실행] [종료]."""

    toggle_visibility_requested = Signal()
    settings_requested = Signal()
    autostart_toggled = Signal(bool)
    """'윈도우 시작 시 실행'을 켜거나 껐다."""
    quit_requested = Signal()
    action_triggered = Signal(str)
    """add_action()으로 추가한 항목이 눌렸다(항목 id)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._menu = QMenu()
        self._toggle_action = QAction(TEXT_HIDE, self._menu)
        self._toggle_action.triggered.connect(self.toggle_visibility_requested)
        self._settings_action = QAction(TEXT_SETTINGS, self._menu)
        self._settings_action.triggered.connect(self.settings_requested)
        self._autostart_action = QAction(TEXT_AUTOSTART, self._menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.triggered.connect(self.autostart_toggled)
        self._quit_action = QAction(TEXT_QUIT, self._menu)
        self._quit_action.triggered.connect(self.quit_requested)
        self._menu.addAction(self._toggle_action)
        self._menu.addAction(self._settings_action)
        self._separator = self._menu.addSeparator()
        self._menu.addAction(self._autostart_action)
        self._menu.addAction(self._quit_action)
        self._actions: dict[str, QAction] = {}

        self._icon = QSystemTrayIcon(_make_icon(), self)
        self._icon.setToolTip(TOOLTIP)
        self._icon.setContextMenu(self._menu)
        self._icon.activated.connect(self._on_activated)

    def show(self) -> None:
        """트레이에 아이콘을 표시한다."""
        self._icon.show()

    def hide(self) -> None:
        """트레이에서 아이콘을 내린다."""
        self._icon.hide()

    def set_widget_visible(self, visible: bool) -> None:
        """위젯 표시 상태에 맞게 메뉴 문구를 바꾼다."""
        self._toggle_action.setText(TEXT_HIDE if visible else TEXT_SHOW)

    def set_autostart_checked(self, checked: bool) -> None:
        """'윈도우 시작 시 실행' 체크 표시를 실제 상태에 맞춘다."""
        self._autostart_action.setChecked(checked)

    def add_action(self, action_id: str, text: str) -> None:
        """구분선 위에 메뉴 항목을 추가한다. 이미 있는 id면(기능 재시작 등) 문구만 바꾼다."""
        if action_id in self._actions:
            self._actions[action_id].setText(text)
            return
        action = QAction(text, self._menu)
        action.triggered.connect(lambda _=False: self.action_triggered.emit(action_id))
        self._menu.insertAction(self._separator, action)
        self._actions[action_id] = action

    def set_action_text(self, action_id: str, text: str) -> None:
        """메뉴 항목 문구를 바꾼다."""
        self._actions[action_id].setText(text)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """아이콘 왼쪽 클릭 시 보이기/숨기기를 토글한다."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility_requested.emit()
