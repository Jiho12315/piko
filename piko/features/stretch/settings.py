"""스트레칭 알림 설정 스키마와 검증."""

import logging
from dataclasses import dataclass
from typing import Any

from piko.core.settings_schema import FieldKind, SettingField

SECONDS_PER_MINUTE = 60
SNOOZE_MIN = 5  # [5분 뒤] 미루기 시간(분). 설정 창에는 두지 않는다

DEFAULTS: dict[str, Any] = {
    "interval_min": 50,  # 알림 간격(분)
    "rest_min": 5,  # [확인] 뒤 휴식 시간(분)
}

TITLE = "스트레칭"
MINUTES_SUFFIX = " 분"
FIELDS: tuple[SettingField, ...] = (
    SettingField(
        "interval_min",
        "알림 간격",
        FieldKind.FLOAT,
        minimum=0.5,
        maximum=240,
        step=1,
        decimals=1,
        suffix=MINUTES_SUFFIX,
    ),
    SettingField(
        "rest_min",
        "휴식 시간",
        FieldKind.FLOAT,
        minimum=0.5,
        maximum=60,
        step=1,
        decimals=1,
        suffix=MINUTES_SUFFIX,
    ),
)

logger = logging.getLogger(__name__)


def _positive_minutes(data: dict[str, Any], key: str) -> float:
    value = data.get(key, DEFAULTS[key])
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        logger.warning(
            "스트레칭 설정 %s=%r이(가) 올바르지 않아 %r을 씁니다", key, value, DEFAULTS[key]
        )
        return float(DEFAULTS[key])
    return float(value)


@dataclass(frozen=True)
class StretchSettings:
    """검증된 스트레칭 알림 설정."""

    interval_min: float
    rest_min: float
    snooze_min: float = SNOOZE_MIN

    @property
    def interval_s(self) -> float:
        """알림 간격(초)."""
        return self.interval_min * SECONDS_PER_MINUTE

    @property
    def rest_s(self) -> float:
        """휴식 시간(초)."""
        return self.rest_min * SECONDS_PER_MINUTE

    @property
    def snooze_s(self) -> float:
        """미루기 시간(초)."""
        return self.snooze_min * SECONDS_PER_MINUTE

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StretchSettings":
        """설정 dict를 검증한다. 잘못된 값은 로그를 남기고 기본값을 쓴다."""
        return cls(
            interval_min=_positive_minutes(data, "interval_min"),
            rest_min=_positive_minutes(data, "rest_min"),
        )
