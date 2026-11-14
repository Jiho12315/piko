"""코드 도트 아이콘 패턴 검사(크기, 색 글자)."""

import pytest

from piko.ui.pixel_icons import ICON_SIZE, PALETTE, PATTERNS


@pytest.mark.parametrize("icon_id", list(PATTERNS))
def test_patterns_are_square_and_use_palette(icon_id: str) -> None:
    rows = PATTERNS[icon_id]
    assert len(rows) == ICON_SIZE
    assert all(len(row) == ICON_SIZE for row in rows)
    assert set("".join(rows)) <= set(PALETTE) | {"."}


def test_menu_icons_exist() -> None:
    assert {"settings", "timer"} <= set(PATTERNS)
