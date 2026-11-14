"""허리 알림 타이머 계산. 현재 시각(now, 초)을 받아서 계산하고 Qt를 쓰지 않는다."""

from enum import StrEnum


class PosturePhase(StrEnum):
    """알림 단계."""

    COUNTING = "counting"  # 다음 알림까지 기다리는 중
    ALERTING = "alerting"  # 알림을 띄운 상태(확인/미루기 대기)
    PAUSED = "paused"  # 일시정지


class PostureScheduler:
    """간격마다 알림, 확인하면 간격 재시작, 미루면 미루기 시간 뒤 재알림, 일시정지/재개."""

    def __init__(self, interval_s: float, snooze_s: float, now: float) -> None:
        if interval_s <= 0 or snooze_s <= 0:
            raise ValueError("간격과 미루기 시간은 0보다 커야 함")
        self._interval_s = interval_s
        self._snooze_s = snooze_s
        self._phase = PosturePhase.COUNTING
        self._due_at = now + interval_s
        self._paused_remaining = 0.0

    @property
    def phase(self) -> PosturePhase:
        """현재 단계."""
        return self._phase

    def remaining(self, now: float) -> float:
        """다음 알림까지 남은 초. 알림 중이면 0, 일시정지 중이면 멈춘 시점의 남은 시간."""
        if self._phase == PosturePhase.COUNTING:
            return max(0.0, self._due_at - now)
        if self._phase == PosturePhase.PAUSED:
            return self._paused_remaining
        return 0.0

    def check(self, now: float) -> bool:
        """알림 시각이 되었으면 알림 단계로 바꾸고 True."""
        if self._phase == PosturePhase.COUNTING and now >= self._due_at:
            self._phase = PosturePhase.ALERTING
            return True
        return False

    def acknowledge(self, now: float) -> None:
        """[확인]: 간격을 처음부터 다시 센다."""
        if self._phase == PosturePhase.ALERTING:
            self._count_from(now, self._interval_s)

    def snooze(self, now: float) -> None:
        """[미루기]: 미루기 시간 뒤 다시 알린다."""
        if self._phase == PosturePhase.ALERTING:
            self._count_from(now, self._snooze_s)

    def pause(self, now: float) -> None:
        """일시정지. 알림 중에 멈추면 재개 시 간격을 처음부터 센다."""
        if self._phase == PosturePhase.COUNTING:
            self._paused_remaining = self.remaining(now)
        elif self._phase == PosturePhase.ALERTING:
            self._paused_remaining = self._interval_s
        else:
            return
        self._phase = PosturePhase.PAUSED

    def resume(self, now: float) -> None:
        """재개. 멈춘 시점의 남은 시간부터 다시 센다."""
        if self._phase == PosturePhase.PAUSED:
            self._count_from(now, self._paused_remaining)

    def _count_from(self, now: float, duration_s: float) -> None:
        self._phase = PosturePhase.COUNTING
        self._due_at = now + duration_s
