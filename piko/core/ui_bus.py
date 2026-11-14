"""기능과 화면 사이의 신호 묶음. 기능은 ui를 import하지 않고 이 버스로만 요청한다.

신호 이름은 범용으로 짓는다(특정 기능 이름을 쓰지 않는다). 연결은 app.py가 한다.
버튼/메뉴 id는 겹치지 않게 "<기능명>.<이름>" 형태로 짓는다.
"""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class DialogButton:
    """대화창 버튼. 눌리면 dialog_button_clicked(id)가 나간다."""

    id: str
    label: str


class UiBus(QObject):
    """기능 → 화면 요청과 화면 → 기능 알림."""

    # 기능 → 화면
    set_character_state = Signal(object)
    """캐릭터 상태를 보여 준다. 값은 상태 이름(str) 또는 후보 목록(list[str], 캐릭터에 있는
    첫 번째를 씀). None이면 평소 동작(돌아다니기)으로 돌아간다."""
    show_dialog = Signal(str, list)
    """대화창에 문구와 버튼(list[DialogButton])을 띄운다."""
    clear_dialog = Signal()
    """대화창 문구와 버튼을 지운다."""
    add_tray_action = Signal(str, str)
    """트레이 메뉴 항목을 추가한다(id, 문구)."""
    set_tray_action_text = Signal(str, str)
    """트레이 메뉴 항목 문구를 바꾼다(id, 문구)."""

    # 화면 → 기능
    dialog_button_clicked = Signal(str)
    """대화창 버튼이 눌렸다(버튼 id)."""
    tray_action_triggered = Signal(str)
    """트레이 메뉴 항목이 눌렸다(항목 id)."""
