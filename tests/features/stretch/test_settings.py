"""스트레칭 설정 검증 테스트."""

from typing import Any

import pytest

from piko.core.settings_schema import normalize_value
from piko.features.stretch.settings import DEFAULTS, FIELDS, StretchSettings


def test_defaults() -> None:
    values = StretchSettings.from_dict(dict(DEFAULTS))
    assert (values.interval_s, values.rest_s, values.snooze_s) == (3000, 300, 300)


def test_fields_match_defaults() -> None:
    assert [f.key for f in FIELDS] == list(DEFAULTS)
    for field in FIELDS:
        assert normalize_value(field, DEFAULTS[field.key]) == DEFAULTS[field.key]


@pytest.mark.parametrize("data", [{"interval_min": 0}, {"rest_min": "5"}, {"rest_min": True}])
def test_invalid_values_fall_back(data: dict[str, Any]) -> None:
    assert StretchSettings.from_dict(data) == StretchSettings.from_dict(dict(DEFAULTS))
