"""프레임 애니메이션 보조 로직(Qt 없이 테스트 가능)."""

MS_PER_SECOND = 1000


def frame_interval_ms(fps: float) -> int:
    """FPS를 타이머 간격(ms)으로 바꾼다. 최소 1ms."""
    if fps <= 0:
        raise ValueError(f"FPS는 0보다 커야 함: {fps}")
    return max(1, round(MS_PER_SECOND / fps))


class FrameCycle:
    """0..count-1을 순환하는 프레임 번호."""

    def __init__(self, count: int) -> None:
        if count < 1:
            raise ValueError(f"프레임 수는 1 이상이어야 함: {count}")
        self._count = count
        self._index = 0

    @property
    def index(self) -> int:
        """현재 프레임 번호."""
        return self._index

    @property
    def count(self) -> int:
        """전체 프레임 수."""
        return self._count

    def advance(self) -> int:
        """다음 프레임으로 넘어가고(끝이면 처음으로) 그 번호를 반환한다."""
        self._index = (self._index + 1) % self._count
        return self._index

    def reset(self) -> None:
        """첫 프레임으로 돌아간다."""
        self._index = 0
