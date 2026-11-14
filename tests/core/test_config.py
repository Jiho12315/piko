"""ConfigStore 테스트."""

from pathlib import Path

from piko.core.config import CORRUPT_SUFFIX, ConfigStore

DEFAULTS = {"interval_min": 30, "sound": False}


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert store.section("posture", DEFAULTS) == DEFAULTS


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "config.json"
    store = ConfigStore(path)
    store.set_section("posture", {"interval_min": 10, "sound": True})
    store.save()

    reloaded = ConfigStore(path)
    reloaded.load()
    assert reloaded.section("posture", DEFAULTS) == {"interval_min": 10, "sound": True}


def test_section_fills_missing_keys_and_drops_unknown(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    store.set_section("posture", {"interval_min": 5, "old_key": 1})
    assert store.section("posture", DEFAULTS) == {"interval_min": 5, "sound": False}


def test_section_returns_copy(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    section = store.section("posture", DEFAULTS)
    section["interval_min"] = 99
    assert store.section("posture", DEFAULTS) == DEFAULTS


def test_corrupt_file_is_backed_up_and_defaults_used(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ 깨진 json", encoding="utf-8")
    store = ConfigStore(path)
    store.load()
    assert store.section("posture", DEFAULTS) == DEFAULTS
    assert not path.exists()
    assert (tmp_path / ("config.json" + CORRUPT_SUFFIX)).exists()


def test_non_object_top_level_is_treated_as_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    store = ConfigStore(path)
    store.load()
    assert store.section("posture", DEFAULTS) == DEFAULTS
