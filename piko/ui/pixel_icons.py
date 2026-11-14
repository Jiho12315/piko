"""메뉴바 도트 아이콘. assets/ui/icon_<id>.png가 있으면 그것을, 없으면 코드로 그린 그림을 쓴다."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from piko.core import paths

ICON_SIZE = 16  # 원본 픽셀
ICON_FILE = "icon_{id}.png"
UI_ASSETS_DIR = "ui"

# 글자 하나 = 픽셀 하나. '.'은 투명
PALETTE = {
    "#": QColor("#5a3c28"),  # 테두리
    "o": QColor("#d9a95b"),  # 톱니 바탕
    "w": QColor("#fffaf0"),  # 시계 바탕
    "k": QColor("#3a2a1e"),  # 시곗바늘
}

PATTERNS: dict[str, tuple[str, ...]] = {
    "settings": (
        "......####......",
        "..##..#oo#..##..",
        ".#oo##oooo##oo#.",
        ".#oooooooooooo#.",
        "..#oooo##oooo#..",
        "###ooo#..#ooo###",
        "#oooo#....#oooo#",
        "#ooo#......#ooo#",
        "#ooo#......#ooo#",
        "#oooo#....#oooo#",
        "###ooo#..#ooo###",
        "..#oooo##oooo#..",
        ".#oooooooooooo#.",
        ".#oo##oooo##oo#.",
        "..##..#oo#..##..",
        "......####......",
    ),
    "timer": (
        ".....######.....",
        "...##wwwwww##...",
        "..#wwwwwwwwww#..",
        ".#wwwwwkwwwwww#.",
        ".#wwwwwkwwwwww#.",
        "#wwwwwwkwwwwwww#",
        "#wwwwwwkwwwwwww#",
        "#wwwwwwkkkkwwww#",
        "#wwwwwwwwwwwwww#",
        "#wwwwwwwwwwwwww#",
        ".#wwwwwwwwwwww#.",
        ".#wwwwwwwwwwww#.",
        "..#wwwwwwwwww#..",
        "...##wwwwww##...",
        ".....######.....",
        "................",
    ),
}


def pattern_image(pattern: tuple[str, ...]) -> QImage:
    """글자 그림을 원본 크기 이미지로 바꾼다."""
    height, width = len(pattern), len(pattern[0])
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    for y, row in enumerate(pattern):
        if len(row) != width:
            raise ValueError(f"아이콘 줄 길이가 다름: {y}번째 줄")
        for x, char in enumerate(row):
            if char != ".":
                image.setPixelColor(x, y, PALETTE[char])
    return image


def icon_pixmap(icon_id: str, size: int) -> QPixmap:
    """아이콘을 size×size로(보간 없이) 만든다. PNG가 있으면 PNG, 없으면 코드 그림."""
    path = paths.asset_path(UI_ASSETS_DIR, ICON_FILE.format(id=icon_id))
    image = QImage(str(path)) if path.is_file() else QImage()
    if image.isNull():
        if icon_id not in PATTERNS:
            raise KeyError(f"아이콘 그림이 없음: {icon_id} (PNG: {path})")
        image = pattern_image(PATTERNS[icon_id])
    return QPixmap.fromImage(
        image.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    )
