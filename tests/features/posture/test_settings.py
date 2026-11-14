"""허리 알림 설정 검증 테스트."""

from typing import Any

import pytest

from piko.core.settings_schema import normalize_value
from piko.features.posture.settings import DEFAULTS, FIELDS, PostureSettings


def test_fields_match_defaults_and_accept_defaults() -> None:
    assert [f.key for f in FIELDS] == list(DEFAULTS)
    for field in FIELDS:
        assert normalize_value(field, DEFAULTS[field.key]) == DEFAULTS[field.key]


def test_defaults() -> None:
    values = PostureSettings.from_dict(dict(DEFAULTS))
    assert values == PostureSettings(interval_min=30, snooze_min=5, sound=False)
    assert values.interval_s == 1800
    assert values.snooze_s == 300


def test_custom_values_and_fractional_minutes() -> None:
    values = PostureSettings.from_dict({"interval_min": 1, "snooze_min": 0.5, "sound": True})
    assert (values.interval_s, values.snooze_s, values.sound) == (60, 30, True)


@pytest.mark.parametrize(
    "data",
    [
        {"interval_min": 0},
        {"interval_min": -5},
        {"interval_min": "30"},
        {"interval_min": True},
        {"snooze_min": None},
        {"sound": "yes"},
    ],
)
def test_invalid_values_fall_back_to_defaults(data: dict[str, Any]) -> None:
    assert PostureSettings.from_dict(data) == PostureSettings.from_dict(dict(DEFAULTS))
