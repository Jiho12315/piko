"""기능 공통 인터페이스(Feature)와 레지스트리."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from piko.core.attention import AttentionCoordinator
from piko.core.config import ConfigStore
from piko.core.settings_schema import SettingField, SettingsSection
from piko.core.ui_bus import UiBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeatureContext:
    """기능이 쓰는 공용 객체: 화면 요청 버스와 알림 우선순위 조율."""

    bus: UiBus
    attention: AttentionCoordinator


@dataclass(frozen=True)
class TimerEntry:
    """타이머 패널에 보일 한 줄. remaining_s가 None이면 시간 없이 status만 보인다."""

    title: str
    remaining_s: float | None
    status: str = ""  # 예: "휴식 중", "일시정지", "알림 중"


class Feature(ABC):
    """모든 기능의 기본 클래스. name과 기본 설정을 정의하고 start/stop을 구현한다.

    화면에는 context.bus로만 요청한다(ui 모듈을 import하지 않는다).
    """

    name: ClassVar[str]
    title: ClassVar[str] = ""
    """설정 창과 타이머 패널에 보일 이름. 비어 있으면 name을 쓴다."""
    attention_priority: ClassVar[int] = 0
    """알림이 겹칠 때의 우선순위. 클수록 먼저."""

    def __init__(self, settings: dict[str, Any], context: FeatureContext) -> None:
        self.settings = settings
        self.context = context

    @property
    def bus(self) -> UiBus:
        """화면 요청 버스."""
        return self.context.bus

    @property
    def attention(self) -> AttentionCoordinator:
        """알림 우선순위 조율."""
        return self.context.attention

    def timer_entries(self) -> list[TimerEntry]:
        """타이머 패널에 보일 남은 시간 정보. 없으면 빈 목록."""
        return []

    @classmethod
    def default_settings(cls) -> dict[str, Any]:
        """이 기능의 설정 스키마(키와 기본값). 설정이 없으면 빈 dict."""
        return {}

    @classmethod
    def settings_fields(cls) -> list[SettingField]:
        """설정 창에 보일 항목. 비어 있으면 설정 창에 나오지 않는다."""
        return []

    @abstractmethod
    def start(self) -> None:
        """기능을 시작한다."""

    @abstractmethod
    def stop(self) -> None:
        """기능을 멈추고 자원을 정리한다."""


class FeatureRegistry:
    """기능 클래스를 등록받아 설정과 함께 생성하고, 한꺼번에 시작/정지한다."""

    def __init__(self, config: ConfigStore, context: FeatureContext) -> None:
        self._config = config
        self._context = context
        self._classes: dict[str, type[Feature]] = {}
        self._instances: dict[str, Feature] = {}

    def register(self, feature_cls: type[Feature]) -> None:
        """기능 클래스를 등록한다. 같은 이름을 두 번 등록하면 ValueError."""
        if feature_cls.name in self._classes:
            raise ValueError(f"이미 등록된 기능: {feature_cls.name}")
        self._classes[feature_cls.name] = feature_cls

    @property
    def features(self) -> list[Feature]:
        """실행 중인 기능 인스턴스 목록(시작 순서)."""
        return list(self._instances.values())

    def start_all(self) -> None:
        """등록된 기능을 설정과 함께 생성하고 시작한다. 설정 파일에 키가 보이게 섹션을 써 둔다."""
        for name in self._classes:
            self._start(name)

    def stop_all(self) -> None:
        """시작한 역순으로 정지한다. 한 기능이 실패해도 나머지는 정지한다."""
        for name in reversed(list(self._instances)):
            self._stop(name)

    def timer_entries(self) -> list[TimerEntry]:
        """실행 중인 기능들의 타이머 정보를 시작 순서대로 모은다(패널이 1초마다 읽는다)."""
        entries: list[TimerEntry] = []
        for feature in self._instances.values():
            entries.extend(feature.timer_entries())
        return entries

    def settings_sections(self) -> list[tuple[SettingsSection, dict[str, Any]]]:
        """설정 창에 보일 기능별 섹션과 현재 값."""
        result = []
        for name, feature_cls in self._classes.items():
            fields = feature_cls.settings_fields()
            if not fields:
                continue
            section = SettingsSection(name, feature_cls.title or name, tuple(fields))
            result.append((section, self._config.section(name, feature_cls.default_settings())))
        return result

    def apply_settings(self, name: str, values: dict[str, Any]) -> None:
        """기능 설정을 바꾸고(모르는 키는 무시) 그 기능만 다시 시작한다.

        파일 저장은 호출한 쪽이 한다.
        """
        feature_cls = self._classes[name]
        current = self._config.section(name, feature_cls.default_settings())
        current.update({key: value for key, value in values.items() if key in current})
        self._config.set_section(name, current)
        was_running = name in self._instances
        if was_running:
            self._stop(name)
            self._start(name)
        logger.info("기능 설정 변경: %s %s", name, current)

    def _start(self, name: str) -> None:
        feature_cls = self._classes[name]
        settings = self._config.section(name, feature_cls.default_settings())
        self._config.set_section(name, settings)
        feature = feature_cls(settings, self._context)
        feature.start()
        self._instances[name] = feature
        logger.info("기능 시작: %s", name)

    def _stop(self, name: str) -> None:
        feature = self._instances.pop(name)
        try:
            feature.stop()
            logger.info("기능 정지: %s", name)
        except Exception:
            logger.exception("기능 정지 실패: %s", name)
