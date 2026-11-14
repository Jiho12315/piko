"""알림 우선순위 조율. 화면(캐릭터·대화창)을 한 번에 한 기능만 쓰게 한다. Qt를 쓰지 않는다.

기능은 알림을 띄우기 전에 try_acquire()로 차지를 요청한다.
- 아무도 없거나 자기가 차지 중이면 성공
- 더 낮은 우선순위가 차지 중이면, 그 기능에 '밀려남'을 알리고(on_preempted) 성공
- 같거나 높은 우선순위가 차지 중이면 실패 → 그 기능은 알림을 건너뛴다
기능끼리는 서로 import하지 않고 이 객체만 공유한다.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class _Member:
    priority: int
    on_preempted: Callable[[], None]


class AttentionCoordinator:
    """화면을 차지한 기능 하나와 기능별 우선순위를 관리한다."""

    def __init__(self) -> None:
        self._members: dict[str, _Member] = {}
        self._holder: str | None = None

    @property
    def holder(self) -> str | None:
        """지금 화면을 차지한 기능 이름."""
        return self._holder

    def register(self, name: str, priority: int, on_preempted: Callable[[], None]) -> None:
        """기능을 등록한다. 다시 등록하면 값을 바꾼다."""
        self._members[name] = _Member(priority, on_preempted)

    def unregister(self, name: str) -> None:
        """기능 등록을 지운다. 차지 중이었으면 놓는다."""
        self.release(name)
        self._members.pop(name, None)

    def try_acquire(self, name: str) -> bool:
        """화면 차지를 요청한다. 차지했으면 True."""
        if name not in self._members:
            raise KeyError(f"등록되지 않은 기능: {name}")
        holder = self._holder
        if holder is None or holder == name:
            self._holder = name
            return True
        if self._members[name].priority <= self._members[holder].priority:
            logger.info("'%s' 알림 건너뜀: '%s'이(가) 화면을 쓰는 중", name, holder)
            return False
        logger.info("'%s'이(가) '%s'의 알림을 대신합니다", name, holder)
        self._holder = name
        self._members[holder].on_preempted()
        return True

    def release(self, name: str) -> None:
        """차지 중이면 놓는다."""
        if self._holder == name:
            self._holder = None
