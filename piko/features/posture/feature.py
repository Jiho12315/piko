"""허리 알림 기능: 스케줄러를 QTimer로 돌리고, 화면에는 UiBus로만 요청한다."""

import logging
import math
import time
import winsound
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QTimer

from piko.core.asset_loader import STATE_ALERT
from piko.core.feature_base import Feature, FeatureContext, TimerEntry
from piko.core.settings_schema import SettingField
from piko.core.ui_bus import DialogButton
from piko.features.posture.scheduler import PosturePhase, PostureScheduler
from piko.features.posture.settings import DEFAULTS, FIELDS, TITLE, PostureSettings

MS_PER_SECOND = 1000
ATTENTION_PRIORITY = 10
CHARACTER_STATES = (STATE_ALERT,)  # 알림 때 쓸 캐릭터 상태(앞쪽이 우선)

BUTTON_OK_ID = "posture.ok"
BUTTON_SNOOZE_ID = "posture.snooze"
TRAY_PAUSE_ID = "posture.pause"

TEXT_ALERT = "허리 펴세요!"
TEXT_OK = "확인"
TEXT_SNOOZE = "{minutes}분 뒤"
TEXT_TRAY_PAUSE = "허리 알림 일시정지"
TEXT_TRAY_RESUME = "허리 알림 재개"
TEXT_TIMER_PAUSED = "일시정지"
TEXT_TIMER_ALERTING = "알림 중"
ALERT_SOUND = winsound.MB_ICONASTERISK

logger = logging.getLogger(__name__)


def _format_minutes(minutes: float) -> str:
    """5.0 → "5", 0.5 → "0.5"."""
    return f"{minutes:g}"


class PostureFeature(Feature):
    """설정 간격마다 '허리 펴세요!' 알림을 띄운다.

    더 높은 우선순위 기능(예: 스트레칭)이 화면을 쓰는 중이면 알림을 건너뛰고 타이머만
    새로 시작한다. 알림 중에 밀려나도 같다.
    """

    name = "posture"
    title = TITLE
    attention_priority = ATTENTION_PRIORITY

    def __init__(
        self,
        settings: dict[str, Any],
        context: FeatureContext,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(settings, context)
        self._values = PostureSettings.from_dict(settings)
        self._clock = clock
        self._scheduler: PostureScheduler | None = None
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
        """간격 30분, 미루기 5분, 소리 끔."""
        return dict(DEFAULTS)

    @classmethod
    def settings_fields(cls) -> list[SettingField]:
        """알림 간격, 미루기 시간, 알림음."""
        return list(FIELDS)

    @property
    def scheduler(self) -> PostureScheduler:
        """스케줄러(시작 후에만 있음)."""
        if self._scheduler is None:
            raise RuntimeError("시작 전에는 스케줄러가 없음")
        return self._scheduler

    def start(self) -> None:
        """타이머를 시작하고 트레이 메뉴를 추가한다."""
        self._scheduler = PostureScheduler(
            self._values.interval_s, self._values.snooze_s, self._clock()
        )
        self.attention.register(self.name, self.attention_priority, self._on_preempted)
        self.bus.dialog_button_clicked.connect(self._on_dialog_button)
        self.bus.tray_action_triggered.connect(self._on_tray_action)
        self.bus.add_tray_action.emit(TRAY_PAUSE_ID, TEXT_TRAY_PAUSE)
        logger.info(
            "허리 알림: 간격 %s분, 미루기 %s분, 소리 %s",
            _format_minutes(self._values.interval_min),
            _format_minutes(self._values.snooze_min),
            self._values.sound,
        )
        self._schedule()

    def stop(self) -> None:
        """타이머를 멈추고 신호 연결을 끊는다. 알림 중이었으면 알림을 닫는다."""
        self._timer.stop()
        if self._scheduler is not None and self._scheduler.phase == PosturePhase.ALERTING:
            self._end_alert()
        self.attention.unregister(self.name)
        self.bus.dialog_button_clicked.disconnect(self._on_dialog_button)
        self.bus.tray_action_triggered.disconnect(self._on_tray_action)

    def timer_entries(self) -> list[TimerEntry]:
        """다음 알림까지 남은 시간."""
        if self._scheduler is None:
            return []
        phase = self._scheduler.phase
        if phase == PosturePhase.ALERTING:
            return [TimerEntry(self.title, None, TEXT_TIMER_ALERTING)]
        remaining = self._scheduler.remaining(self._clock())
        status = TEXT_TIMER_PAUSED if phase == PosturePhase.PAUSED else ""
        return [TimerEntry(self.title, remaining, status)]

    def _on_timer(self) -> None:
        now = self._clock()
        if self.scheduler.check(now):
            if self.attention.try_acquire(self.name):
                self._show_alert()
            else:
                self.scheduler.acknowledge(now)  # 다른 알림이 먼저: 타이머만 새로 시작
        self._schedule()

    def _on_preempted(self) -> None:
        """더 높은 우선순위 알림이 화면을 가져갔다: 알림을 닫고 타이머를 새로 시작한다."""
        if self.scheduler.phase == PosturePhase.ALERTING:
            self.scheduler.acknowledge(self._clock())
            self._end_alert(release=False)
            self._schedule()

    def _show_alert(self) -> None:
        logger.info("허리 알림 표시")
        self.bus.set_character_state.emit(list(CHARACTER_STATES))
        self.bus.show_dialog.emit(TEXT_ALERT, self._buttons)
        if self._values.sound:
            winsound.MessageBeep(ALERT_SOUND)

    def _end_alert(self, release: bool = True) -> None:
        self.bus.clear_dialog.emit()
        self.bus.set_character_state.emit(None)
        if release:
            self.attention.release(self.name)

    def _on_dialog_button(self, button_id: str) -> None:
        if self.scheduler.phase != PosturePhase.ALERTING:
            return
        now = self._clock()
        if button_id == BUTTON_OK_ID:
            self.scheduler.acknowledge(now)
        elif button_id == BUTTON_SNOOZE_ID:
            self.scheduler.snooze(now)
        else:
            return  # 다른 기능의 버튼
        logger.info("허리 알림 응답: %s", button_id)
        self._end_alert()
        self._schedule()

    def _on_tray_action(self, action_id: str) -> None:
        if action_id != TRAY_PAUSE_ID:
            return  # 다른 기능의 메뉴
        now = self._clock()
        if self.scheduler.phase == PosturePhase.PAUSED:
            self.scheduler.resume(now)
            self.bus.set_tray_action_text.emit(TRAY_PAUSE_ID, TEXT_TRAY_PAUSE)
            logger.info("허리 알림 재개")
        else:
            was_alerting = self.scheduler.phase == PosturePhase.ALERTING
            self.scheduler.pause(now)
            if was_alerting:
                self._end_alert()
            self.bus.set_tray_action_text.emit(TRAY_PAUSE_ID, TEXT_TRAY_RESUME)
            logger.info("허리 알림 일시정지")
        self._schedule()

    def _schedule(self) -> None:
        """대기 중이면 알림 시각에 깨어나도록 예약한다."""
        if self.scheduler.phase != PosturePhase.COUNTING:
            self._timer.stop()
            return
        remaining = self.scheduler.remaining(self._clock())
        self._timer.start(math.ceil(remaining * MS_PER_SECOND))
