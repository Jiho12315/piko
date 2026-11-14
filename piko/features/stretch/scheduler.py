"""스트레칭 알림 타이머 계산. 현재 시각(now, 초)을 받아서 계산하고 Qt를 쓰지 않는다.

간격 카운트 → 알림 → [확인] → 휴식 → 휴식 끝 → 다시 간격 카운트.
알림 중 [미루기] → 미루기 시간 뒤 다시 알림.
"""

from enum import StrEnum


class StretchPhase(StrEnum):
    """스트레칭 단계."""

    COUNTING = "counting"  # 다음 알림까지 기다리는 중
    ALERTING = "alerting"  # 알림을 띄운 상태(확인/미루기 대기)
    RESTING = "resting"  # [확인] 뒤 휴식 중


class StretchEvent(StrEnum):
    """check()가 알려 주는 일."""

    NONE = "none"
    ALERT = "alert"  # 알림 시각이 됨
    REST_DONE = "rest_done"  # 휴식이 끝나 다시 카운트 시작


class StretchScheduler:
    """스트레칭 알림 상태 기계."""

    def __init__(self, interval_s: float, rest_s: float, snooze_s: float, now: float) -> None:
        if min(interval_s, rest_s, snooze_s) <= 0:
            raise ValueError("간격, 휴식, 미루기 시간은 0보다 커야 함")
        self._interval_s = interval_s
        self._rest_s = rest_s
        self._snooze_s = snooze_s
        self._phase = StretchPhase.COUNTING
        self._due_at = now + interval_s

    @property
    def phase(self) -> StretchPhase:
        """현재 단계."""
        return self._phase

    def remaining(self, now: float) -> float:
        """대기 중이면 알림까지, 휴식 중이면 휴식 끝까지 남은 초. 알림 중이면 0."""
        if self._phase == StretchPhase.ALERTING:
            return 0.0
        return max(0.0, self._due_at - now)

    def check(self, now: float) -> StretchEvent:
        """예정 시각이 지났으면 다음 단계로 넘어가고 무슨 일이 일어났는지 알려 준다."""
        if self._phase == StretchPhase.ALERTING or now < self._due_at:
            return StretchEvent.NONE
        if self._phase == StretchPhase.COUNTING:
            self._phase = StretchPhase.ALERTING
            return StretchEvent.ALERT
        self._count_from(now, self._interval_s)
        return StretchEvent.REST_DONE

    def acknowledge(self, now: float) -> None:
        """[확인]: 휴식을 시작한다."""
        if self._phase == StretchPhase.ALERTING:
            self._phase = StretchPhase.RESTING
            self._due_at = now + self._rest_s

    def snooze(self, now: float) -> None:
        """[미루기]: 미루기 시간 뒤 다시 알린다."""
        if self._phase == StretchPhase.ALERTING:
            self._count_from(now, self._snooze_s)

    def _count_from(self, now: float, duration_s: float) -> None:
        self._phase = StretchPhase.COUNTING
        self._due_at = now + duration_s
