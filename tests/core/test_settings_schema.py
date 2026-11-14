"""설정 스키마 테스트."""

import pytest

from piko.core.settings_schema import FieldKind, SettingField, normalize_value

INT_FIELD = SettingField("scale", "배율", FieldKind.INT, minimum=1, maximum=8)
FLOAT_FIELD = SettingField("m", "분", FieldKind.FLOAT, minimum=0.5, maximum=60, decimals=1)
BOOL_FIELD = SettingField("sound", "소리", FieldKind.BOOL)


@pytest.mark.parametrize(("value", "expected"), [(3, 3), (3.6, 4), (0, 1), (99, 8)])
def test_int_is_rounded_and_clamped(value: float, expected: int) -> None:
    result = normalize_value(INT_FIELD, value)
    assert result == expected and isinstance(result, int)


@pytest.mark.parametrize(
    ("value", "expected", "kind"),
    [(30.0, 30, int), (0.5, 0.5, float), (1.25, 1.2, float), (0.1, 0.5, float), (100, 60, int)],
)
def test_float_keeps_decimals_and_whole_numbers_become_int(
    value: float, expected: float, kind: type
) -> None:
    result = normalize_value(FLOAT_FIELD, value)
    assert result == expected and isinstance(result, kind)


def test_bool() -> None:
    assert normalize_value(BOOL_FIELD, 1) is True
    assert normalize_value(BOOL_FIELD, False) is False


def test_invalid_range_rejected() -> None:
    with pytest.raises(ValueError):
        SettingField("x", "x", FieldKind.INT, minimum=5, maximum=1)
