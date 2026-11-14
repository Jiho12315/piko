"""캐릭터 상태와 프레임 재생. 프레임은 배율만큼 미리 확대하고 좌우 반전본도 만들어 둔다."""

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap

from piko.core.asset_loader import STATE_IDLE, CharacterSpec
from piko.ui.animation import FrameCycle, frame_interval_ms
from piko.ui.pixel_art import load_pixel_image


class CharacterAnimator(QObject):
    """현재 상태·방향의 프레임을 FPS에 맞춰 돌린다. 그리기는 scene_view가 한다.

    어느 폴더를 쓸지(walk_left/walk_right/반전)는 CharacterSpec.frame_source()가 정한다.
    재생 중이 아니거나(set_running(False)) 프레임이 1장이면 타이머를 돌리지 않는다.
    """

    frame_changed = Signal()

    def __init__(self, spec: CharacterSpec, scale: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._spec = spec
        # 폴더별 [(원본, 좌우 반전본), ...]
        self._frames: dict[str, list[tuple[QPixmap, QPixmap]]] = {}
        for folder, files in spec.frames.items():
            pairs = []
            for file in files:
                image = load_pixel_image(file, scale)
                flipped = image.flipped(Qt.Orientation.Horizontal)
                pairs.append((QPixmap.fromImage(image), QPixmap.fromImage(flipped)))
            self._frames[folder] = pairs
        self._state = STATE_IDLE
        self._facing_right = True
        self._running = False
        self._folder, self._flip = spec.frame_source(self._state, self._facing_right)
        self._cycle = FrameCycle(len(self._frames[self._folder]))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)

    @property
    def spec(self) -> CharacterSpec:
        """캐릭터 정보."""
        return self._spec

    @property
    def state(self) -> str:
        """현재 상태."""
        return self._state

    @property
    def facing_right(self) -> bool:
        """오른쪽을 보고 있는지."""
        return self._facing_right

    @property
    def frame_index(self) -> int:
        """현재 프레임 번호."""
        return self._cycle.index

    @property
    def source(self) -> tuple[str, bool]:
        """지금 쓰는 (프레임 폴더, 좌우 반전 여부)."""
        return self._folder, self._flip

    @property
    def is_animating(self) -> bool:
        """프레임 타이머가 돌고 있는지."""
        return self._timer.isActive()

    def set_state(self, state: str) -> None:
        """상태를 바꾸고 첫 프레임부터 재생한다. 같은 상태면 그대로 둔다."""
        if state not in self._spec.states:
            raise ValueError(f"'{self._spec.id}'에 없는 상태: {state}")
        if state == self._state:
            return
        self._state = state
        self._select_source(restart=True)

    def set_facing_right(self, facing_right: bool) -> None:
        """보는 방향을 바꾼다. 쓰는 폴더가 바뀌면 첫 프레임부터 재생한다."""
        if facing_right == self._facing_right:
            return
        self._facing_right = facing_right
        self._select_source(restart=False)

    def set_running(self, running: bool) -> None:
        """재생을 켜거나 끈다(화면에 안 보이면 끈다)."""
        self._running = running
        self._update_timer()

    def current_pixmap(self) -> QPixmap:
        """지금 그릴 프레임."""
        original, flipped = self._frames[self._folder][self._cycle.index]
        return flipped if self._flip else original

    def _select_source(self, restart: bool) -> None:
        folder, flip = self._spec.frame_source(self._state, self._facing_right)
        if restart or folder != self._folder:
            self._cycle = FrameCycle(len(self._frames[folder]))
        self._folder, self._flip = folder, flip
        self._update_timer()
        self.frame_changed.emit()

    def _update_timer(self) -> None:
        if self._running and self._cycle.count > 1:
            self._timer.start(frame_interval_ms(self._spec.fps[self._folder]))
        else:
            self._timer.stop()

    def _next_frame(self) -> None:
        self._cycle.advance()
        self.frame_changed.emit()
