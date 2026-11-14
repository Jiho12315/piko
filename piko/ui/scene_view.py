"""방 장면: 배경 → 캐릭터 순서로 그리고, 돌아다니기를 시간에 맞춰 진행한다."""

import math
import random

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer
from PySide6.QtGui import QHideEvent, QPainter, QPaintEvent, QPixmap, QShowEvent
from PySide6.QtWidgets import QWidget

from piko.core.asset_loader import STATE_IDLE, STATE_WALK, CharacterSpec, RoomSpec
from piko.ui.animation import MS_PER_SECOND
from piko.ui.character_view import CharacterAnimator
from piko.ui.pixel_art import load_pixel_image
from piko.ui.wander import Wander, WanderConfig, WanderPhase, pixel_x

# 걷는 중에는 그릴 x가 1px 바뀌는 시각마다 깨어난다(속도 36px/s면 약 28ms).
# 너무 빨라지지 않게 최소 간격을 둔다. 쉬는 중에는 쉬기가 끝날 때 한 번만 깨어난다.
MIN_WALK_TICK_MS = 8
NS_PER_SECOND = 1_000_000_000


class SceneView(QWidget):
    """방 배경 위에서 캐릭터가 바닥선을 따라 좌우로 돌아다닌다."""

    def __init__(
        self,
        room: RoomSpec,
        character: CharacterSpec,
        scale: int,
        rng: random.Random | None = None,
        parent: QWidget | None = None,
        start_x: float | None = None,
    ) -> None:
        """start_x가 없으면 이동 범위 가운데에서 시작한다."""
        super().__init__(parent)
        self._room = room
        self._scale = scale
        self._background = QPixmap.fromImage(load_pixel_image(room.background, scale))
        self.setFixedSize(room.size[0] * scale, room.size[1] * scale)

        self._animator = CharacterAnimator(character, scale, self)
        self._animator.frame_changed.connect(lambda: self.update(self._character_rect()))

        low, high = room.walk_range
        config = WanderConfig(min_x=low, max_x=high, speed=character.walk_speed)
        if start_x is None:
            start_x = (low + high) / 2
        self._wander = Wander(config, start_x=start_x, rng=rng or random.Random())
        self._override_state: str | None = None
        self._drawn_x = pixel_x(self._wander.x)

        self._tick = QTimer(self)
        self._tick.setSingleShot(True)
        # 기본(Coarse) 타이머는 윈도우에서 15.6ms 단위로 늘어져 걸음이 고르지 않다
        self._tick.setTimerType(Qt.TimerType.PreciseTimer)
        self._tick.timeout.connect(self._on_tick)
        self._clock = QElapsedTimer()

    @property
    def animator(self) -> CharacterAnimator:
        """캐릭터 애니메이터."""
        return self._animator

    @property
    def wander(self) -> Wander:
        """돌아다니기 상태."""
        return self._wander

    def set_override_state(self, state: str | None) -> None:
        """돌아다니기를 멈추고 state를 보여 준다. None이면 다시 돌아다닌다."""
        self._override_state = state
        if state is None:
            self._wander.resume()
            self._clock.start()
        else:
            self._wander.stop()
        self._apply_wander()
        self._schedule()

    def _on_tick(self) -> None:
        # restart()는 ms 정수라 1px 경계에 못 미칠 수 있어 ns로 잰다
        dt = self._clock.nsecsElapsed() / NS_PER_SECOND
        self._clock.restart()
        self._wander.update(dt)
        self._apply_wander()
        self._schedule()

    def _apply_wander(self) -> None:
        """돌아다니기 상태를 캐릭터 상태·방향·위치에 반영한다."""
        if self._override_state is not None:
            self._animator.set_state(self._override_state)
        elif self._wander.phase == WanderPhase.WALKING:
            self._animator.set_state(STATE_WALK)
        else:
            self._animator.set_state(STATE_IDLE)
        self._animator.set_facing_right(self._wander.facing_right)
        x = pixel_x(self._wander.x)
        if x != self._drawn_x:  # 원본 1px 단위로 움직일 때만, 캐릭터 주변만 다시 그린다
            old = self._character_rect()
            self._drawn_x = x
            self.update(old.united(self._character_rect()))

    def _character_rect(self) -> QRect:
        """지금 캐릭터가 그려지는 영역(화면 좌표)."""
        anchor_x, anchor_y = self._animator.spec.anchor
        width, height = self._animator.spec.frame_size
        return QRect(
            (self._drawn_x - anchor_x) * self._scale,
            (self._room.floor_y - anchor_y) * self._scale,
            width * self._scale,
            height * self._scale,
        )

    def _schedule(self) -> None:
        """다음에 깨어날 시점을 정한다. 멈춤 상태나 숨김 상태면 타이머를 끈다."""
        phase = self._wander.phase
        if not self.isVisible() or phase == WanderPhase.STOPPED:
            self._tick.stop()
        elif phase == WanderPhase.WALKING:
            wait_ms = math.ceil(self._wander.seconds_to_next_pixel() * MS_PER_SECOND)
            self._tick.start(max(MIN_WALK_TICK_MS, wait_ms))
        else:
            self._tick.start(max(1, math.ceil(self._wander.rest_remaining * MS_PER_SECOND)))

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 (Qt 재정의)
        """보이면 애니메이션과 돌아다니기를 시작한다."""
        super().showEvent(event)
        self._animator.set_running(True)
        self._clock.start()
        self._apply_wander()
        self._schedule()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        """숨겨지면 모든 타이머를 멈춘다(CPU 절약)."""
        super().hideEvent(event)
        self._animator.set_running(False)
        self._tick.stop()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """배경 → 캐릭터 순서로 그린다. 캐릭터 위치는 원본 픽셀 격자에 맞춘다."""
        painter = QPainter(self)
        painter.setClipRegion(event.region())  # 바뀐 영역만 다시 그린다
        painter.drawPixmap(0, 0, self._background)
        painter.drawPixmap(self._character_rect().topLeft(), self._animator.current_pixmap())
