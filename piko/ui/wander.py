"""좌우 돌아다니기 로직. 경과 시간(dt)만 받아 위치를 계산하고 Qt를 쓰지 않는다.

쉬기(RESTING) → 범위 안의 임의 x로 걷기(WALKING) → 쉬기 … 를 반복한다.
알림 등으로 멈추면(STOPPED) 그 자리에 서 있고, 다시 시작하면 잠깐 쉰 뒤 걷는다.
"""

import math
import random
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_REST_MIN_S = 2.0
DEFAULT_REST_MAX_S = 6.0
DEFAULT_MIN_WALK_DISTANCE = 16.0
# 걷기마다 최소한 이만큼은 움직여서 update()의 반복이 반드시 끝나게 한다.
MIN_STEP = 1.0
# 픽셀 경계를 확실히 넘도록 더하는 아주 작은 거리
BOUNDARY_EPSILON = 1e-6


def pixel_x(x: float) -> int:
    """화면에 그릴 정수 x(반올림, .5는 항상 올림)."""
    return math.floor(x + 0.5)


class WanderPhase(StrEnum):
    """돌아다니기 단계."""

    RESTING = "resting"
    WALKING = "walking"
    STOPPED = "stopped"


@dataclass(frozen=True)
class WanderConfig:
    """이동 범위(x)와 속도(초당 px), 쉬는 시간(초), 한 번에 걷는 최소 거리(px)."""

    min_x: float
    max_x: float
    speed: float
    rest_min_s: float = DEFAULT_REST_MIN_S
    rest_max_s: float = DEFAULT_REST_MAX_S
    min_walk_distance: float = DEFAULT_MIN_WALK_DISTANCE

    def __post_init__(self) -> None:
        if not self.min_x < self.max_x:
            raise ValueError(f"min_x({self.min_x})는 max_x({self.max_x})보다 작아야 함")
        if self.speed <= 0:
            raise ValueError(f"speed는 0보다 커야 함: {self.speed}")
        if not 0 <= self.rest_min_s <= self.rest_max_s:
            raise ValueError("0 <= rest_min_s <= rest_max_s 이어야 함")
        if self.min_walk_distance < 0:
            raise ValueError("min_walk_distance는 0 이상이어야 함")


class Wander:
    """바닥선 위에서 x만 바뀌는 돌아다니기 상태 기계."""

    def __init__(self, config: WanderConfig, start_x: float, rng: random.Random) -> None:
        self._config = config
        self._rng = rng
        self._x = min(max(start_x, config.min_x), config.max_x)
        self._target = self._x
        self._facing_right = True
        self._phase = WanderPhase.RESTING
        self._rest_left = 0.0
        self._start_rest()

    @property
    def x(self) -> float:
        """현재 x."""
        return self._x

    @property
    def target_x(self) -> float:
        """걷는 중이면 목표 x, 아니면 현재 x."""
        return self._target

    @property
    def facing_right(self) -> bool:
        """오른쪽을 보고 있는지."""
        return self._facing_right

    @property
    def phase(self) -> WanderPhase:
        """현재 단계."""
        return self._phase

    @property
    def rest_remaining(self) -> float:
        """쉬는 중이면 남은 시간(초), 아니면 0."""
        return self._rest_left if self._phase == WanderPhase.RESTING else 0.0

    def seconds_to_next_pixel(self) -> float:
        """걷는 중일 때, 그릴 x(pixel_x)가 1 바뀌거나 목표에 도착하기까지 남은 초.

        이 시각에 맞춰 깨어나면 1px씩 고른 간격으로 움직인다. 걷는 중이 아니면 0.
        """
        if self._phase != WanderPhase.WALKING:
            return 0.0
        drawn = pixel_x(self._x)
        # 경계에 딱 맞추면 부동소수점 오차로 아직 이전 픽셀일 수 있어 아주 조금 넘긴다
        if self._facing_right:
            to_boundary = (drawn + 0.5) - self._x + BOUNDARY_EPSILON
        else:
            to_boundary = self._x - (drawn - 0.5) + BOUNDARY_EPSILON
        to_target = abs(self._target - self._x)
        return min(to_boundary, to_target) / self._config.speed

    def update(self, dt: float) -> None:
        """dt초만큼 진행한다. 한 번에 여러 단계(쉬기 끝 → 걷기 → 도착 → 쉬기)를 넘을 수 있다."""
        if dt < 0:
            raise ValueError(f"dt는 0 이상이어야 함: {dt}")
        remaining = dt
        while remaining > 0 and self._phase != WanderPhase.STOPPED:
            if self._phase == WanderPhase.RESTING:
                if remaining < self._rest_left:
                    self._rest_left -= remaining
                    return
                remaining -= self._rest_left
                self._start_walk()
            else:
                distance = abs(self._target - self._x)
                travel = self._config.speed * remaining
                if travel < distance:
                    self._x += travel if self._facing_right else -travel
                    return
                self._x = self._target
                remaining -= distance / self._config.speed
                self._start_rest()

    def stop(self) -> None:
        """그 자리에 멈춘다."""
        self._phase = WanderPhase.STOPPED
        self._target = self._x

    def resume(self) -> None:
        """멈춘 상태면 잠깐 쉰 뒤 다시 돌아다닌다."""
        if self._phase == WanderPhase.STOPPED:
            self._start_rest()

    def _start_rest(self) -> None:
        self._phase = WanderPhase.RESTING
        self._target = self._x
        self._rest_left = self._rng.uniform(self._config.rest_min_s, self._config.rest_max_s)

    def _start_walk(self) -> None:
        self._target = self._pick_target()
        self._facing_right = self._target > self._x
        self._phase = WanderPhase.WALKING

    def _pick_target(self) -> float:
        """현재 위치에서 최소 거리 이상 떨어진 범위 안의 임의 x. 범위가 좁으면 먼 쪽 끝."""
        cfg = self._config
        gap = max(cfg.min_walk_distance, MIN_STEP)
        left_len = max(0.0, (self._x - gap) - cfg.min_x)
        right_len = max(0.0, cfg.max_x - (self._x + gap))
        if left_len + right_len <= 0:
            return cfg.min_x if self._x - cfg.min_x > cfg.max_x - self._x else cfg.max_x
        pick = self._rng.uniform(0, left_len + right_len)
        if pick < left_len:
            return cfg.min_x + pick
        return self._x + gap + (pick - left_len)
