"""방 장면 + 대화창 묶음. 배율을 바꾸면 둘을 새로 만들고 보이던 상태를 그대로 옮긴다."""

import logging
from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLayout, QVBoxLayout, QWidget

from piko.core.asset_loader import STATE_IDLE, CharacterSpec, RoomSpec
from piko.core.ui_bus import DialogButton
from piko.ui.dialog_box import DialogBox
from piko.ui.scene_view import SceneView

logger = logging.getLogger(__name__)


class PikoView(QWidget):
    """위는 방 장면, 아래는 대화창. UiBus 요청은 이 위젯이 받아 알맞은 쪽에 전달한다."""

    button_clicked = Signal(str)

    def __init__(
        self, room: RoomSpec, character: CharacterSpec, scale: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._room = room
        self._character = character
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        # 배율을 바꿔 다시 만들 때 옮겨 줄 상태
        self._override_state: str | None = None
        self._message: tuple[str, list[DialogButton]] | None = None
        self._scene: SceneView | None = None
        self._dialog: DialogBox | None = None
        self._scale = 0
        self._build(scale)

    @property
    def scale(self) -> int:
        """현재 배율."""
        return self._scale

    @property
    def scene(self) -> SceneView:
        """방 장면."""
        assert self._scene is not None
        return self._scene

    @property
    def dialog(self) -> DialogBox:
        """대화창."""
        assert self._dialog is not None
        return self._dialog

    def set_scale(self, scale: int) -> None:
        """배율을 바꾼다. 캐릭터 위치, 알림 상태, 대화창 내용은 유지한다."""
        if scale != self._scale:
            self._build(scale)

    def set_override_state(self, state: str | list[str] | None) -> None:
        """캐릭터 상태를 보여 준다. 후보 목록이면 캐릭터에 있는 첫 상태를 쓴다.

        None이면 다시 돌아다닌다. 후보가 하나도 없으면 로그를 남기고 대기 상태로 멈춘다.
        """
        resolved = None
        if state is not None:
            resolved = self._character.first_available(state)
            if resolved is None:
                logger.warning("캐릭터 '%s'에 없는 상태 %s → 대기", self._character.id, state)
                resolved = STATE_IDLE
        self._override_state = resolved
        self.scene.set_override_state(resolved)

    def show_message(self, text: str, buttons: Sequence[DialogButton] = ()) -> None:
        """대화창에 문구와 버튼을 띄운다."""
        self._message = (text, list(buttons))
        self.dialog.show_message(text, buttons)

    def clear(self) -> None:
        """대화창을 비운다."""
        self._message = None
        self.dialog.clear()

    def _build(self, scale: int) -> None:
        start_x = self._scene.wander.x if self._scene is not None else None
        scene = SceneView(self._room, self._character, scale, start_x=start_x)
        dialog = DialogBox(self._room.size[0], scale)
        dialog.button_clicked.connect(self.button_clicked)
        if self._override_state is not None:
            scene.set_override_state(self._override_state)
        if self._message is not None:
            dialog.show_message(*self._message)

        for old in (self._scene, self._dialog):
            if old is not None:
                self._layout.removeWidget(old)
                old.hide()
                old.deleteLater()
        self._layout.addWidget(scene)
        self._layout.addWidget(dialog)
        self._scene, self._dialog, self._scale = scene, dialog, scale
        # 보이는 위젯에 추가된 자식은 Qt가 나중에 표시한다. 크기를 바로 계산하려면 지금 표시해야
        # 창이 새 크기로 맞출 수 있다.
        if self.isVisible():
            scene.show()
            dialog.show()
        self._layout.activate()
