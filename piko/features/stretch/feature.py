"""스트레칭 알림 기능: 간격마다 알림, [확인]하면 휴식, 휴식이 끝나면 다시 카운트.

알림부터 휴식이 끝날 때까지 화면 차지(attention)를 쥐고 있어서, 그동안 오는 낮은
우선순위 알림(허리 알림)은 건너뛰어진다.
"""

import logging
import math
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QTimer

from piko.core.asset_loader import STATE_ALERT
from piko.core.feature_base import Feature, FeatureContext, TimerEntry
from piko.core.settings_schema import SettingField
from piko.core.ui_bus import DialogButton
from piko.features.stretch.scheduler import StretchEvent, StretchPhase, StretchScheduler
from piko.features.stretch.settings import DEFAULTS, FIELDS, TITLE, StretchSettings

MS_PER_SECOND = 1000
ATTENTION_PRIORITY = 20  # 허리 알림(10)보다 우선
# 알림 때 쓸 캐릭터 상태(앞쪽이 우선). 캐릭터에 stretch 폴더가 생기면 자동으로 그걸 쓴다.
CHARACTER_STATES = ("stretch", STATE_ALERT)

BUTTON_OK_ID = "stretch.ok"
BUTTON_SNOOZE_ID = "stretch.snooze"

TEXT_ALERT = "스트레칭할 시간!"
TEXT_OK = "확인"
TEXT_SNOOZE = "{minutes}분 뒤"
TEXT_TIMER_RESTING = "휴식 중"
TEXT_TIMER_ALERTING = "알림 중"

logger = logging.getLogger(__name__)


def _format_minutes(minutes: float) -> str:
    return f"{minutes:g}"


class StretchFeature(Feature):
    """설정 간격마다 '스트레칭할 시간!' 알림을 띄우고, 확인하면 휴식 시간을 센다."""

    name = "stretch"
    title = TITLE
    attention_priority = ATTENTION_PRIORITY

    def __init__(
        self,
        settings: dict[str, Any],
        context: FeatureContext,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(settings, context)
        self._values = StretchSettings.from_dict(settings)
        self._clock = clock
        self._scheduler: StretchScheduler | None = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)
        self._buttons = [
            DialogButton(BUTTON_OK_ID, TEXT_OK),
            DialogButton(
                BUTTON_SNOOZE_ID,
                TEXT_SNOOZE.format(minutes=_format_minutes(self._values.snooze_min)),
            ),
        ]

    @classmethod
    def default_settings(cls) -> dict[str, Any]:
        """간격 50분, 휴식 5분."""
        return dict(DEFAULTS)

    @classmethod
    def settings_fields(cls) -> list[SettingField]:
        """알림 간격, 휴식 시간."""
        return list(FIELDS)

    @property
    def scheduler(self) -> StretchScheduler:
        """스케줄러(시작 후에만 있음)."""
        if self._scheduler is None:
            raise RuntimeError("시작 전에는 스케줄러가 없음")
        return self._scheduler

    def start(self) -> None:
        """타이머를 시작한다."""
        v = self._values
        self._scheduler = StretchScheduler(v.interval_s, v.rest_s, v.snooze_s, self._clock())
        self.attention.register(self.name, self.attention_priority, self._on_preempted)
        self.bus.dialog_button_clicked.connect(self._on_dialog_button)
        logger.info(
            "스트레칭 알림: 간격 %s분, 휴식 %s분",
            _format_minutes(v.interval_min),
            _format_minutes(v.rest_min),
        )
        self._schedule()

    def stop(self) -> None:
        """타이머를 멈추고 신호 연결을 끊는다. 알림 중이었으면 알림을 닫는다."""
        self._timer.stop()
        if self._scheduler is not None and self._scheduler.phase == StretchPhase.ALERTING:
            self._end_alert()
        self.attention.unregister(self.name)
        self.bus.dialog_button_clicked.disconnect(self._on_dialog_button)

    def timer_entries(self) -> list[TimerEntry]:
        """다음 알림까지 또는 휴식 끝까지 남은 시간."""
        if self._scheduler is None:
            return []
        phase = self._scheduler.phase
        if phase == StretchPhase.ALERTING:
            return [TimerEntry(self.title, None, TEXT_TIMER_ALERTING)]
        remaining = self._scheduler.remaining(self._clock())
        status = TEXT_TIMER_RESTING if phase == StretchPhase.RESTING else ""
        return [TimerEntry(self.title, remaining, status)]

    def _on_timer(self) -> None:
        event = self.scheduler.check(self._clock())
        if event == StretchEvent.ALERT:
            if self.attention.try_acquire(self.name):
                self._show_alert()
            else:  # 더 높은 우선순위가 있을 때만(지금은 없음): 미루기처럼 처리
                self.scheduler.snooze(self._clock())
        elif event == StretchEvent.REST_DONE:
            logger.info("스트레칭 휴식 끝")
            self.attention.release(self.name)
        self._schedule()

    def _on_preempted(self) -> None:
        """더 높은 우선순위 알림에 밀려났다(지금은 없음): 알림을 닫고 미룬다."""
        if self.scheduler.phase == StretchPhase.ALERTING:
            self.scheduler.snooze(self._clock())
            self.bus.clear_dialog.emit()
            self.bus.set_character_state.emit(None)
        self._schedule()

    def _show_alert(self) -> None:
        logger.info("스트레칭 알림 표시")
        self.bus.set_character_state.emit(list(CHARACTER_STATES))
        self.bus.show_dialog.emit(TEXT_ALERT, self._buttons)

    def _end_alert(self) -> None:
        self.bus.clear_dialog.emit()
        self.bus.set_character_state.emit(None)
        self.attention.release(self.name)

    def _on_dialog_button(self, button_id: str) -> None:
        if self.scheduler.phase != StretchPhase.ALERTING:
            return
        now = self._clock()
        if button_id == BUTTON_OK_ID:
            # 휴식 중에도 화면 차지를 유지한다(그동안 허리 알림을 건너뜀)
            self.scheduler.acknowledge(now)
            self.bus.clear_dialog.emit()
            self.bus.set_character_state.emit(None)
            logger.info("스트레칭 휴식 시작")
        elif button_id == BUTTON_SNOOZE_ID:
            self.scheduler.snooze(now)
            self._end_alert()
            logger.info("스트레칭 알림 미루기")
        else:
            return  # 다른 기능의 버튼
        self._schedule()

    def _schedule(self) -> None:
        """대기·휴식 중이면 예정 시각에 깨어나도록 예약한다."""
        if self.scheduler.phase == StretchPhase.ALERTING:
            self._timer.stop()
            return
        remaining = self.scheduler.remaining(self._clock())
        self._timer.start(math.ceil(remaining * MS_PER_SECOND))
