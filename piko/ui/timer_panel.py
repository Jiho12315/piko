"""타이머 패널: 기능들이 제공하는 남은 시간(TimerEntry)을 이름과 mm:ss로 나열한다.

펼쳐져 있을 때만 1초마다 다시 읽고 그린다. 접혀 있으면 타이머가 돌지 않는다.
"""

import math
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QHideEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from piko.core.feature_base import TimerEntry
from piko.ui import theme

PANEL_WIDTH = 196  # 24px 글꼴로 "휴식 중 00:00"(160px)이 들어가게
PADDING = 10
ROW_SPACING = 6
REFRESH_MS = 1000
SECONDS_PER_MINUTE = 60

TEXT_HEADER = "타이머"
TEXT_EMPTY = "알림 없음"


def format_mmss(seconds: float) -> str:
    """남은 초를 mm:ss로(올림). 60분이 넘으면 분이 세 자리가 될 수 있다."""
    total = max(0, math.ceil(seconds))
    minutes, secs = divmod(total, SECONDS_PER_MINUTE)
    return f"{minutes:02d}:{secs:02d}"


def entry_text(entry: TimerEntry) -> str:
    """패널에 보일 시간 문구. 예: "49:59", "휴식 중 04:12", "알림 중"."""
    if entry.remaining_s is None:
        return entry.status
    time_text = format_mmss(entry.remaining_s)
    return f"{entry.status} {time_text}" if entry.status else time_text


class TimerPanel(QWidget):
    """provider()가 돌려주는 TimerEntry 목록을 보여 준다. 새 기능이 생겨도 이 코드는 그대로다."""

    def __init__(
        self, provider: Callable[[], list[TimerEntry]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._provider = provider
        self.setFixedWidth(PANEL_WIDTH)
        margin = theme.BORDER_WIDTH + PADDING
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(ROW_SPACING)
        header = QLabel(TEXT_HEADER, self)
        header.setFont(theme.ui_font(bold=True))
        header.setStyleSheet(theme.label_style())
        self._layout.addWidget(header)
        self._rows: list[tuple[QLabel, QLabel]] = []
        self._empty = QLabel(TEXT_EMPTY, self)
        self._empty.setFont(theme.ui_font())
        self._empty.setStyleSheet(theme.label_style(muted=True))
        self._layout.addWidget(self._empty)
        self._layout.addStretch(1)
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

    @property
    def is_refreshing(self) -> bool:
        """1초 갱신 타이머가 돌고 있는지."""
        return self._timer.isActive()

    def texts(self) -> list[tuple[str, str]]:
        """지금 보이는 (이름, 시간) 목록."""
        return [(title.text(), value.text()) for title, value in self._rows]

    def refresh(self) -> None:
        """기능들의 남은 시간을 다시 읽어 표시한다."""
        entries = self._provider()
        if len(entries) != len(self._rows):
            self._rebuild_rows(len(entries))
        for (title, value), entry in zip(self._rows, entries, strict=True):
            title.setText(entry.title)
            value.setText(entry_text(entry))
        self._empty.setVisible(not entries)

    def _rebuild_rows(self, count: int) -> None:
        for title, value in self._rows:
            for label in (title, value):
                self._layout.removeWidget(label)
                label.deleteLater()
        self._rows = []
        insert_at = 1  # 머리글 다음
        for _ in range(count):
            title = QLabel(self)
            title.setFont(theme.ui_font())
            title.setStyleSheet(theme.label_style(muted=True))
            value = QLabel(self)
            value.setFont(theme.ui_font(theme.FONT_SIZE_LARGE))  # 남은 시간은 크게
            value.setStyleSheet(theme.label_style())
            value.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self._layout.insertWidget(insert_at, title)
            self._layout.insertWidget(insert_at + 1, value)
            # 보이는 위젯에 새로 넣은 자식은 Qt가 나중에 표시한다. 펼친 즉시 보이도록 바로 표시
            title.show()
            value.show()
            insert_at += 2
            self._rows.append((title, value))
        self._layout.activate()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 (Qt 재정의)
        """펼쳐지면 바로 갱신하고 1초 타이머를 켠다."""
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        """접히면 타이머를 끈다(CPU 절약)."""
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """테두리와 바탕을 그린다."""
        theme.paint_frame(QPainter(self), self.rect())
