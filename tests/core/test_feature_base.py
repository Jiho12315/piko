"""Feature 기본 클래스와 레지스트리 테스트."""

from pathlib import Path
from typing import Any

import pytest

from piko.core.attention import AttentionCoordinator
from piko.core.config import ConfigStore
from piko.core.feature_base import Feature, FeatureContext, FeatureRegistry, TimerEntry
from piko.core.settings_schema import FieldKind, SettingField
from piko.core.ui_bus import UiBus

INTERVAL_FIELD = SettingField("interval_min", "간격", FieldKind.INT, minimum=1, maximum=60)


class DummyFeature(Feature):
    name = "dummy"
    events: list[str] = []

    @classmethod
    def default_settings(cls) -> dict[str, Any]:
        return {"interval_min": 30}

    def start(self) -> None:
        DummyFeature.events.append(f"start:{self.name}:{self.settings['interval_min']}")

    def stop(self) -> None:
        DummyFeature.events.append(f"stop:{self.name}")


class OtherFeature(DummyFeature):
    name = "other"


class ConfigurableFeature(DummyFeature):
    name = "configurable"
    title = "설정 가능"

    @classmethod
    def settings_fields(cls) -> list[SettingField]:
        return [INTERVAL_FIELD]


class BrokenStopFeature(DummyFeature):
    name = "broken"

    def stop(self) -> None:
        raise RuntimeError("정지 실패")


@pytest.fixture(autouse=True)
def clear_events() -> None:
    DummyFeature.events.clear()


@pytest.fixture
def config(tmp_path: Path) -> ConfigStore:
    return ConfigStore(tmp_path / "config.json")


@pytest.fixture
def bus() -> FeatureContext:
    """(이름은 예전 그대로) 기능에 넘길 공용 객체."""
    return FeatureContext(UiBus(), AttentionCoordinator())


def test_start_all_passes_merged_settings_and_bus(config: ConfigStore, bus: FeatureContext) -> None:
    config.set_section("dummy", {"interval_min": 1})
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.start_all()
    feature = registry.features[0]
    assert feature.settings == {"interval_min": 1}
    assert feature.context is bus
    assert feature.bus is bus.bus
    assert feature.attention is bus.attention


class TimedFeature(DummyFeature):
    name = "timed"
    title = "타이머 있음"

    def timer_entries(self) -> list[TimerEntry]:
        return [TimerEntry(self.title, 12.0, "휴식 중")]


def test_timer_entries_collects_from_running_features(
    config: ConfigStore, bus: FeatureContext
) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)  # 타이머 없음 → 기본 빈 목록
    registry.register(TimedFeature)
    assert registry.timer_entries() == []  # 시작 전
    registry.start_all()
    assert registry.timer_entries() == [TimerEntry("타이머 있음", 12.0, "휴식 중")]
    registry.stop_all()
    assert registry.timer_entries() == []


def test_start_all_writes_section_with_defaults(config: ConfigStore, bus: FeatureContext) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.start_all()
    config.save()
    reloaded = ConfigStore(config.path)
    reloaded.load()
    assert reloaded.section("dummy", {"interval_min": -1}) == {"interval_min": 30}


def test_start_in_order_stop_in_reverse(config: ConfigStore, bus: FeatureContext) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.register(OtherFeature)
    registry.start_all()
    registry.stop_all()
    assert DummyFeature.events == [
        "start:dummy:30",
        "start:other:30",
        "stop:other",
        "stop:dummy",
    ]
    assert registry.features == []


def test_settings_sections_only_for_features_with_fields(
    config: ConfigStore, bus: FeatureContext
) -> None:
    config.set_section("configurable", {"interval_min": 7})
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.register(ConfigurableFeature)
    sections = registry.settings_sections()
    assert len(sections) == 1
    section, values = sections[0]
    assert (section.name, section.title, section.fields) == (
        "configurable",
        "설정 가능",
        (INTERVAL_FIELD,),
    )
    assert values == {"interval_min": 7}


def test_apply_settings_restarts_only_that_feature(
    config: ConfigStore, bus: FeatureContext
) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.register(ConfigurableFeature)
    registry.start_all()
    DummyFeature.events.clear()
    registry.apply_settings("configurable", {"interval_min": 5, "unknown": 1})
    assert DummyFeature.events == ["stop:configurable", "start:configurable:5"]
    assert config.section("configurable", {"interval_min": 0, "unknown": None}) == {
        "interval_min": 5,
        "unknown": None,
    }
    assert {f.name for f in registry.features} == {"dummy", "configurable"}


def test_duplicate_register_raises(config: ConfigStore, bus: FeatureContext) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    with pytest.raises(ValueError):
        registry.register(DummyFeature)


def test_stop_failure_does_not_block_others(config: ConfigStore, bus: FeatureContext) -> None:
    registry = FeatureRegistry(config, bus)
    registry.register(DummyFeature)
    registry.register(BrokenStopFeature)
    registry.start_all()
    registry.stop_all()
    assert "stop:dummy" in DummyFeature.events


def test_feature_without_start_cannot_be_created(bus: FeatureContext) -> None:
    class Incomplete(Feature):
        name = "incomplete"

    with pytest.raises(TypeError):
        Incomplete({}, bus)  # type: ignore[abstract]
