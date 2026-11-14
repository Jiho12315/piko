"""설정 항목 설명(스키마). 설정 창은 이 목록만 보고 입력칸을 만든다."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FieldKind(StrEnum):
    """설정 값의 종류."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"


@dataclass(frozen=True)
class SettingField:
    """설정 항목 하나. 숫자는 minimum~maximum 범위로 제한된다."""

    key: str
    label: str
    kind: FieldKind
    minimum: float = 0
    maximum: float = 0
    step: float = 1
    decimals: int = 0
    suffix: str = ""

    def __post_init__(self) -> None:
        if self.kind != FieldKind.BOOL and self.minimum > self.maximum:
            raise ValueError(f"'{self.key}': minimum이 maximum보다 큼")


@dataclass(frozen=True)
class SettingsSection:
    """config.json의 섹션 하나와 그 항목들."""

    name: str
    title: str
    fields: tuple[SettingField, ...]


def normalize_value(field: SettingField, value: Any) -> Any:
    """입력값을 종류에 맞게 바꾸고 범위 안으로 자른다. 정수로 떨어지는 실수는 정수로 저장한다."""
    if field.kind == FieldKind.BOOL:
        return bool(value)
    number = min(max(float(value), field.minimum), field.maximum)
    if field.kind == FieldKind.INT:
        return round(number)
    number = round(number, field.decimals)
    return int(number) if number.is_integer() else number
