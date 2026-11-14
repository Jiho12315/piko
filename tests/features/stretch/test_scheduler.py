"""스트레칭 타이머 계산 테스트."""

import pytest

from piko.features.stretch.scheduler import StretchEvent, StretchPhase, StretchScheduler

INTERVAL, REST, SNOOZE = 3000.0, 300.0, 300.0


def make(now: float = 0.0) -> StretchScheduler:
    return StretchScheduler(INTERVAL, REST, SNOOZE, now)


def test_counts_then_alerts() -> None:
    s = make()
    assert s.remaining(100) == INTERVAL - 100
    assert s.check(INTERVAL - 1) == StretchEvent.NONE
    assert s.check(INTERVAL) == StretchEvent.ALERT
    assert s.phase == StretchPhase.ALERTING
    assert s.remaining(INTERVAL + 10) == 0
    assert s.check(INTERVAL + 999) == StretchEvent.NONE  # 응답할 때까지 그대로


def test_acknowledge_rests_then_counts_again() -> None:
    s = make()
    s.check(INTERVAL)
    s.acknowledge(4000)
    assert s.phase == StretchPhase.RESTING
    assert s.remaining(4100) == REST - 100
    assert s.check(4000 + REST - 1) == StretchEvent.NONE
    assert s.check(4000 + REST) == StretchEvent.REST_DONE
    assert s.phase == StretchPhase.COUNTING
    assert s.remaining(4000 + REST) == INTERVAL


def test_snooze_alerts_again_after_snooze() -> None:
    s = make()
    s.check(INTERVAL)
    s.snooze(4000)
    assert s.phase == StretchPhase.COUNTING
    assert s.remaining(4000) == SNOOZE
    assert s.check(4000 + SNOOZE) == StretchEvent.ALERT


def test_acknowledge_and_snooze_ignored_when_not_alerting() -> None:
    s = make()
    s.acknowledge(10)
    s.snooze(10)
    assert s.phase == StretchPhase.COUNTING
    assert s.remaining(10) == INTERVAL - 10


def test_invalid_durations() -> None:
    for args in ((0, REST, SNOOZE), (INTERVAL, 0, SNOOZE), (INTERVAL, REST, -1)):
        with pytest.raises(ValueError):
            StretchScheduler(*args, 0)
