"""프레임 애니메이션 보조 로직 테스트."""

import pytest

from piko.ui.animation import FrameCycle, frame_interval_ms


def test_frame_cycle_loops() -> None:
    cycle = FrameCycle(3)
    assert [cycle.advance() for _ in range(4)] == [1, 2, 0, 1]
    cycle.reset()
    assert cycle.index == 0


def test_frame_cycle_single_frame_stays() -> None:
    cycle = FrameCycle(1)
    assert cycle.advance() == 0


def test_frame_cycle_rejects_zero() -> None:
    with pytest.raises(ValueError):
        FrameCycle(0)


def test_frame_interval_ms() -> None:
    assert frame_interval_ms(2) == 500
    assert frame_interval_ms(12) == 83
    with pytest.raises(ValueError):
        frame_interval_ms(0)
