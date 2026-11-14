"""기능 테스트 공용 도구: 가짜 시계, 버스 기록기."""

from typing import Any

from piko.core.ui_bus import UiBus


class FakeClock:
    """테스트가 직접 옮기는 시계(초)."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Recorder:
    """버스 신호를 순서대로 기록한다."""

    def __init__(self, bus: UiBus) -> None:
        self.calls: list[tuple[str, Any]] = []
        bus.set_character_state.connect(lambda s: self.calls.append(("state", s)))
        bus.show_dialog.connect(lambda t, b: self.calls.append(("dialog", (t, b))))
        bus.clear_dialog.connect(lambda: self.calls.append(("clear", None)))
        bus.add_tray_action.connect(lambda i, t: self.calls.append(("tray_add", (i, t))))
        bus.set_tray_action_text.connect(lambda i, t: self.calls.append(("tray_text", (i, t))))

    def last(self, kind: str) -> Any:
        return next(value for k, value in reversed(self.calls) if k == kind)

    def kinds(self) -> list[str]:
        return [k for k, _ in self.calls]

    def dialogs(self) -> list[str]:
        """띄운 대화창 문구 목록."""
        return [value[0] for k, value in self.calls if k == "dialog"]
