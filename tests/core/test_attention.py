"""알림 우선순위 조율 테스트."""

import pytest

from piko.core.attention import AttentionCoordinator


@pytest.fixture
def coordinator() -> AttentionCoordinator:
    return AttentionCoordinator()


def test_first_request_wins_and_release(coordinator: AttentionCoordinator) -> None:
    coordinator.register("a", 10, lambda: None)
    assert coordinator.try_acquire("a")
    assert coordinator.try_acquire("a")  # 이미 내 것
    assert coordinator.holder == "a"
    coordinator.release("a")
    assert coordinator.holder is None


def test_lower_or_equal_priority_is_refused(coordinator: AttentionCoordinator) -> None:
    coordinator.register("high", 20, lambda: None)
    coordinator.register("low", 10, lambda: None)
    coordinator.register("same", 20, lambda: None)
    assert coordinator.try_acquire("high")
    assert not coordinator.try_acquire("low")
    assert not coordinator.try_acquire("same")
    assert coordinator.holder == "high"


def test_higher_priority_preempts(coordinator: AttentionCoordinator) -> None:
    preempted: list[str] = []
    coordinator.register("low", 10, lambda: preempted.append("low"))
    coordinator.register("high", 20, lambda: None)
    assert coordinator.try_acquire("low")
    assert coordinator.try_acquire("high")
    assert preempted == ["low"]
    assert coordinator.holder == "high"


def test_release_by_non_holder_is_ignored(coordinator: AttentionCoordinator) -> None:
    coordinator.register("a", 10, lambda: None)
    coordinator.register("b", 10, lambda: None)
    coordinator.try_acquire("a")
    coordinator.release("b")
    assert coordinator.holder == "a"


def test_unregister_releases(coordinator: AttentionCoordinator) -> None:
    coordinator.register("a", 10, lambda: None)
    coordinator.try_acquire("a")
    coordinator.unregister("a")
    assert coordinator.holder is None
    with pytest.raises(KeyError):
        coordinator.try_acquire("a")
