"""위젯 테마: 색, 테두리, 글꼴, 버튼 스타일.

대화창·메뉴바·타이머 패널·설정 창이 모두 여기서 가져온다.
"""

import logging

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter

from piko.core import paths

logger = logging.getLogger(__name__)

# --- 색 ---
BACKGROUND_COLOR = QColor("#f4ead2")  # 베이지 바탕
BORDER_COLOR = QColor("#5a3c28")  # 갈색 테두리
DIVIDER_COLOR = QColor("#cdb48e")  # 연한 갈색 구분선
INPUT_COLOR = QColor("#fffaf0")  # 입력칸 바탕
TEXT_COLOR = "#3a2a1e"
MUTED_TEXT_COLOR = "#8a7560"
BUTTON_COLOR = "#ffd27f"
BUTTON_HOVER_COLOR = "#ffe2a8"
BUTTON_ACTIVE_COLOR = "#f0b85a"
TOGGLE_OFF_COLOR = QColor("#d8c7a8")
TOGGLE_ON_COLOR = QColor("#e8a948")

# --- 테두리 ---
BORDER_WIDTH = 3  # 위젯 창 안의 대화창·메뉴바·패널
POPUP_BORDER_WIDTH = 2  # 설정 창 같은 팝업, 버튼, 입력칸

# --- 글꼴 ---
FONT_DIR = "fonts"
FONT_FILES = ("Galmuri11.ttf", "Galmuri11-Bold.ttf")
# Galmuri11은 12px 격자로 그려진 글꼴이라 11px에서는 획이 빠진다("간"→"긴"). 12px와 그 2배를 쓴다
FONT_SIZE = 12
FONT_SIZE_LARGE = 24
_font_family: str | None = None  # load_fonts() 전에는 기본 글꼴


def load_fonts() -> str | None:
    """assets/fonts의 도트 글꼴을 앱에 등록한다. QApplication을 만든 뒤 한 번 부른다.

    파일이 없거나 읽을 수 없으면 로그를 남기고 기본 글꼴을 쓴다. 등록한 글꼴 이름을 반환한다.
    """
    global _font_family
    families: list[str] = []
    for name in FONT_FILES:
        path = paths.asset_path(FONT_DIR, name)
        font_id = QFontDatabase.addApplicationFont(str(path)) if path.is_file() else -1
        if font_id < 0:
            logger.warning("글꼴을 불러오지 못해 기본 글꼴을 씁니다: %s", path)
            continue
        families.extend(QFontDatabase.applicationFontFamilies(font_id))
    _font_family = families[0] if families else None
    if _font_family:
        logger.info("글꼴: %s", _font_family)
    return _font_family


def ui_font(size: int = FONT_SIZE, bold: bool = False) -> QFont:
    """UI 글꼴. 도트가 뭉개지지 않게 안티앨리어싱을 끈다."""
    font = QFont(_font_family) if _font_family else QFont()
    font.setPixelSize(size)
    font.setBold(bold)
    font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


# --- 그리기 / 스타일시트 ---


def paint_frame(painter: QPainter, rect: QRect, border: int = BORDER_WIDTH) -> None:
    """각진 갈색 테두리와 베이지 바탕을 그린다."""
    painter.fillRect(rect, BORDER_COLOR)
    painter.fillRect(rect.adjusted(border, border, -border, -border), BACKGROUND_COLOR)


def label_style(muted: bool = False) -> str:
    """글자색 스타일."""
    return f"color: {MUTED_TEXT_COLOR if muted else TEXT_COLOR};"


def button_style(border: int = POPUP_BORDER_WIDTH, padding: int = 8) -> str:
    """대화창·설정 창의 각진 노란 버튼."""
    return (
        f"QPushButton {{ background: {BUTTON_COLOR}; color: {TEXT_COLOR};"
        f" border: {border}px solid {BORDER_COLOR.name()}; border-radius: 0px;"
        f" padding: 2px {padding}px; }}"
        f"QPushButton:hover {{ background: {BUTTON_HOVER_COLOR}; }}"
        f"QPushButton:pressed {{ background: {BUTTON_ACTIVE_COLOR}; }}"
    )


def tool_button_style(padding: int) -> str:
    """메뉴바 아이콘 버튼."""
    return (
        f"QToolButton {{ background: transparent; border: none; padding: {padding}px; }}"
        f"QToolButton:hover {{ background: {BUTTON_HOVER_COLOR}; }}"
        f"QToolButton:checked {{ background: {BUTTON_ACTIVE_COLOR}; }}"
    )


def input_style() -> str:
    """숫자 입력칸(각진 갈색 테두리, 밝은 바탕)."""
    return (
        f"QLineEdit {{ background: {INPUT_COLOR.name()}; color: {TEXT_COLOR};"
        f" border: {POPUP_BORDER_WIDTH}px solid {BORDER_COLOR.name()}; border-radius: 0px;"
        f" padding: 1px 4px; selection-background-color: {BUTTON_COLOR};"
        f" selection-color: {TEXT_COLOR}; }}"
    )
