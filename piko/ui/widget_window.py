"""피코 위젯 창: 테두리 없음, 항상 맨 위, 드래그 이동. 크기는 내용물에 맞춘다."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QLayout, QVBoxLayout, QWidget

SCREEN_MARGIN = 16
# 저장된 위치를 복원할 때, 창이 어느 화면에든 이만큼(px)은 보여야 그 위치를 쓴다
MIN_VISIBLE_PX = 48


def bottom_right_position(available: QRect, size: QSize, margin: int) -> QPoint:
    """작업 영역(available) 우측 하단에 size 크기 창을 margin만큼 띄워 놓을 좌상단 좌표."""
    x = available.x() + available.width() - size.width() - margin
    y = available.y() + available.height() - size.height() - margin
    return QPoint(x, y)


def is_visible_enough(rect: QRect, screens: Sequence[QRect], min_visible: int) -> bool:
    """rect가 어느 한 화면에 가로·세로 min_visible px 이상 걸쳐 있으면 True."""
    need_w = min(min_visible, rect.width())
    need_h = min(min_visible, rect.height())
    for screen in screens:
        overlap = rect.intersected(screen)
        if overlap.width() >= need_w and overlap.height() >= need_h:
            return True
    return False


def clamp_into(rect: QRect, area: QRect) -> QPoint:
    """rect가 area 안에 들어가도록 옮긴 좌상단 좌표. area보다 크면 좌상단을 맞춘다."""
    x = max(area.x(), min(rect.x(), area.x() + area.width() - rect.width()))
    y = max(area.y(), min(rect.y(), area.y() + area.height() - rect.height()))
    return QPoint(x, y)


def _activate_layouts(widget: QWidget) -> None:
    """자식 위젯의 레이아웃부터(안쪽→바깥쪽) 다시 계산한다."""
    for child in widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
        _activate_layouts(child)
    layout = widget.layout()
    if layout is not None:
        layout.activate()


class WidgetWindow(QWidget):
    """항상 맨 위에 떠 있는 위젯 창. 포커스를 뺏지 않는다.

    내용물은 add_content()로 위에서 아래로 쌓는다. 내용물이 처리하지 않은 왼쪽 드래그는
    창 이동으로 쓴다.
    """

    moved = Signal(QPoint)
    """드래그 이동이 끝났을 때 새 좌상단 좌표를 보낸다."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # 작업표시줄에 표시하지 않음
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self._drag_offset: QPoint | None = None

    def add_content(self, widget: QWidget) -> None:
        """창 아래쪽에 위젯을 추가한다."""
        self._layout.addWidget(widget)

    def place(self, saved: QPoint | None) -> None:
        """저장된 위치가 화면 안에 충분히 보이면 그곳에, 아니면 기본 위치(우측 하단)에 둔다."""
        self._fit_to_content()
        if saved is not None:
            screens = [screen.availableGeometry() for screen in QGuiApplication.screens()]
            if is_visible_enough(QRect(saved, self.size()), screens, MIN_VISIBLE_PX):
                self.move(saved)
                return
        self.move_to_default_position()

    def move_to_default_position(self) -> None:
        """주 화면 작업 영역의 우측 하단으로 옮긴다."""
        self._fit_to_content()
        screen = QGuiApplication.primaryScreen()
        self.move(bottom_right_position(screen.availableGeometry(), self.size(), SCREEN_MARGIN))

    def refit_keeping_bottom_right(self, change: Callable[[], None]) -> QPoint:
        """change()로 내용물 크기를 바꾼 뒤, 오른쪽 아래 모서리를 그대로 두고 화면 안에 맞춘다.

        새 좌상단 좌표를 반환한다.
        """
        old = self.geometry()
        change()
        self._fit_to_content()
        size = self.size()
        top_left = QPoint(
            old.x() + old.width() - size.width(), old.y() + old.height() - size.height()
        )
        screen = QGuiApplication.screenAt(old.center()) or QGuiApplication.primaryScreen()
        position = clamp_into(QRect(top_left, size), screen.availableGeometry())
        self.move(position)
        return position

    def refit_in_screen(self, change: Callable[[], None]) -> QPoint:
        """change()로 내용물 크기를 바꾼 뒤, 왼쪽 위를 그대로 두되 화면 밖으로 나가면 안으로 민다.

        (타이머 패널을 펼쳐 오른쪽으로 넓어질 때) 새 좌상단 좌표를 반환한다.
        """
        old = self.geometry()
        change()
        self._fit_to_content()
        screen = QGuiApplication.screenAt(old.center()) or QGuiApplication.primaryScreen()
        position = clamp_into(QRect(old.topLeft(), self.size()), screen.availableGeometry())
        self.move(position)
        return position

    def _fit_to_content(self) -> None:
        """안쪽 레이아웃부터 크기를 다시 계산하고 창을 맞춘다."""
        _activate_layouts(self)
        self.adjustSize()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt 재정의)
        """왼쪽 버튼으로 드래그를 시작한다."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """드래그 중이면 마우스를 따라 이동한다."""
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """드래그를 끝내고 moved 시그널을 보낸다."""
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self.moved.emit(self.pos())
            event.accept()
            return
        super().mouseReleaseEvent(event)
