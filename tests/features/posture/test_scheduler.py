"""허리 알림 타이머 계산 테스트."""

import pytest

from piko.features.posture.scheduler import PosturePhase, PostureScheduler

INTERVAL = 1800.0
SNOOZE = 300.0


def make(now: float = 0.0) -> PostureScheduler:
    return PostureScheduler(INTERVAL, SNOOZE, now)


def test_counts_down_and_alerts_when_due() -> None:
    s = make()
    assert s.phase == PosturePhase.COUNTING
    assert s.remaining(100) == INTERVAL - 100
    assert s.check(INTERVAL - 1) is False
    assert s.check(INTERVAL) is True
    assert s.phase == PosturePhase.ALERTING
    assert s.remaining(INTERVAL + 50) == 0
    assert s.check(INTERVAL + 1) is False  # 이미 알림 중


def test_acknowledge_restarts_full_interval() -> None:
    s = make()
    s.check(INTERVAL)
    s.acknowledge(2000)
    assert s.phase == PosturePhase.COUNTING
    assert s.remaining(2000) == INTERVAL


def test_snooze_alerts_again_after_snooze() -> None:
    s = make()
    s.check(INTERVAL)
    s.snooze(2000)
    assert s.remaining(2000) == SNOOZE
    assert s.check(2000 + SNOOZE - 1) is False
    assert s.check(2000 + SNOOZE) is True


def test_acknowledge_and_snooze_ignored_when_not_alerting() -> None:
    s = make()
    s.acknowledge(500)
    s.snooze(500)
    assert s.remaining(500) == INTERVAL - 500


def test_pause_keeps_remaining_and_resume_continues() -> None:
    s = make()
    s.pause(600)
    assert s.phase == PosturePhase.PAUSED
    assert s.remaining(99999) == INTERVAL - 600  # 멈춘 동안 줄지 않음
    assert s.check(99999) is False
    s.resume(5000)
    assert s.phase == PosturePhase.COUNTING
    assert s.remaining(5000) == INTERVAL - 600
    assert s.check(5000 + INTERVAL - 600) is True


def test_pause_while_alerting_resumes_with_full_interval() -> None:
    s = make()
    s.check(INTERVAL)
    s.pause(INTERVAL + 10)
    s.resume(3000)
    assert s.remaining(3000) == INTERVAL


def test_pause_twice_and_resume_when_counting_are_noops() -> None:
    s = make()
    s.resume(10)
    assert s.remaining(10) == INTERVAL - 10
    s.pause(100)
    s.pause(500)
    assert s.remaining(0) == INTERVAL - 100


def test_invalid_durations() -> None:
    with pytest.raises(ValueError):
        PostureScheduler(0, SNOOZE, 0)
    with pytest.raises(ValueError):
        PostureScheduler(INTERVAL, -1, 0)
