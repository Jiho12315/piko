"""타이머 패널 문구 테스트."""

import pytest

from piko.core.feature_base import TimerEntry
from piko.ui.timer_panel import entry_text, format_mmss


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "00:00"),
        (0.2, "00:01"),
        (59.0, "00:59"),
        (60, "01:00"),
        (3000, "50:00"),
        (7260, "121:00"),
        (-3, "00:00"),
    ],
)
def test_format_mmss_rounds_up(seconds: float, text: str) -> None:
    assert format_mmss(seconds) == text


@pytest.mark.parametrize(
    ("entry", "text"),
    [
        (TimerEntry("허리 알림", 1799.5), "30:00"),
        (TimerEntry("스트레칭", 252, "휴식 중"), "휴식 중 04:12"),
        (TimerEntry("허리 알림", None, "알림 중"), "알림 중"),
    ],
)
def test_entry_text(entry: TimerEntry, text: str) -> None:
    assert entry_text(entry) == text
