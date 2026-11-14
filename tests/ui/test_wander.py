"""좌우 돌아다니기 로직 테스트."""

import random

import pytest

from piko.ui.wander import Wander, WanderConfig, WanderPhase, pixel_x

CONFIG = WanderConfig(
    min_x=20, max_x=172, speed=24, rest_min_s=2, rest_max_s=6, min_walk_distance=16
)


def make(start_x: float = 96, seed: int = 1, config: WanderConfig = CONFIG) -> Wander:
    return Wander(config, start_x=start_x, rng=random.Random(seed))


def test_starts_resting_at_start_x() -> None:
    wander = make()
    assert wander.phase == WanderPhase.RESTING
    assert wander.x == 96
    assert CONFIG.rest_min_s <= wander.rest_remaining <= CONFIG.rest_max_s


def test_start_x_is_clamped_to_range() -> None:
    assert make(start_x=0).x == CONFIG.min_x
    assert make(start_x=999).x == CONFIG.max_x


def test_rest_ends_then_walks_toward_target() -> None:
    wander = make()
    wander.update(wander.rest_remaining)
    assert wander.phase == WanderPhase.WALKING
    assert abs(wander.target_x - wander.x) >= CONFIG.min_walk_distance
    assert wander.facing_right == (wander.target_x > wander.x)


def test_walks_at_configured_speed() -> None:
    wander = make()
    wander.update(wander.rest_remaining)
    start, target = wander.x, wander.target_x
    wander.update(0.25)
    assert wander.x == pytest.approx(start + (6 if target > start else -6))


def test_arrives_then_rests_with_leftover_time() -> None:
    wander = make()
    wander.update(wander.rest_remaining)
    travel_time = abs(wander.target_x - wander.x) / CONFIG.speed
    target = wander.target_x
    wander.update(travel_time + 0.5)
    assert wander.x == pytest.approx(target)
    assert wander.phase == WanderPhase.RESTING


def test_stays_in_range_over_long_run() -> None:
    wander = make(seed=7)
    walks = 0
    previous = wander.phase
    for _ in range(20_000):
        wander.update(0.05)
        assert CONFIG.min_x <= wander.x <= CONFIG.max_x
        if wander.phase == WanderPhase.WALKING and previous != WanderPhase.WALKING:
            walks += 1
            assert wander.facing_right == (wander.target_x > wander.x)
        previous = wander.phase
    assert walks > 50  # 1000초 동안 여러 번 걸었다


def test_one_big_update_equals_many_small_updates() -> None:
    a, b = make(seed=3), make(seed=3)
    a.update(30.0)
    for _ in range(600):
        b.update(0.05)
    assert a.x == pytest.approx(b.x)
    assert a.phase == b.phase


def test_stop_freezes_and_resume_rests_first() -> None:
    wander = make()
    wander.update(wander.rest_remaining + 0.5)
    wander.stop()
    x = wander.x
    wander.update(100)
    assert wander.phase == WanderPhase.STOPPED
    assert wander.x == x
    wander.resume()
    assert wander.phase == WanderPhase.RESTING
    assert wander.x == x


def test_narrow_range_still_moves() -> None:
    config = WanderConfig(min_x=0, max_x=10, speed=5, rest_min_s=0, rest_max_s=0)
    wander = make(start_x=5, config=config)
    wander.update(0.01)
    assert wander.phase == WanderPhase.WALKING
    assert wander.target_x in (0, 10)


def test_zero_rest_does_not_hang() -> None:
    config = WanderConfig(min_x=0, max_x=100, speed=50, rest_min_s=0, rest_max_s=0)
    wander = make(start_x=50, config=config)
    wander.update(60.0)
    assert 0 <= wander.x <= 100


@pytest.mark.parametrize(
    ("x", "expected"), [(10.0, 10), (10.49, 10), (10.5, 11), (11.5, 12), (-0.5, 0)]
)
def test_pixel_x_rounds_half_up(x: float, expected: int) -> None:
    assert pixel_x(x) == expected


def start_walking(target: float, start_x: float = 100.0) -> Wander:
    wander = make(start_x=start_x)
    wander._target, wander._facing_right = target, target > start_x
    wander._phase = WanderPhase.WALKING
    return wander


def test_seconds_to_next_pixel_is_zero_when_not_walking() -> None:
    assert make().seconds_to_next_pixel() == 0


@pytest.mark.parametrize("target", [170.0, 30.0])
def test_walking_by_next_pixel_moves_exactly_one_pixel_each_time(target: float) -> None:
    wander = start_walking(target)
    drawn = [pixel_x(wander.x)]
    while wander.phase == WanderPhase.WALKING:
        wait = wander.seconds_to_next_pixel()
        assert 0 < wait <= 1 / CONFIG.speed + 1e-6  # 1px 이동 시간을 넘지 않는다
        wander.update(wait)
        drawn.append(pixel_x(wander.x))
    steps = [b - a for a, b in zip(drawn, drawn[1:], strict=False)]
    direction = 1 if target > 100 else -1
    # 걷는 동안은 매번 정확히 1px. 마지막은 도착해서 쉬기로 넘어가는 갱신이라 0px일 수 있다
    assert set(steps[:-1]) == {direction}
    assert steps[-1] in (0, direction)
    assert drawn[-1] == target


def test_seconds_to_next_pixel_stops_at_target() -> None:
    wander = start_walking(100.2, start_x=100.0)  # 목표가 픽셀 경계보다 가깝다
    assert wander.seconds_to_next_pixel() == pytest.approx(0.2 / CONFIG.speed)


def test_negative_dt_rejected() -> None:
    with pytest.raises(ValueError):
        make().update(-0.1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_x": 10, "max_x": 10, "speed": 1},
        {"min_x": 0, "max_x": 10, "speed": 0},
        {"min_x": 0, "max_x": 10, "speed": 1, "rest_min_s": 5, "rest_max_s": 1},
        {"min_x": 0, "max_x": 10, "speed": 1, "min_walk_distance": -1},
    ],
)
def test_invalid_config(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        WanderConfig(**kwargs)
