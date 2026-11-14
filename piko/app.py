"""앱 초기화와 기능 등록. 각 계층을 조립하는 곳이다."""

import logging
from typing import Any

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from piko import __version__
from piko.core import autostart, paths
from piko.core.asset_loader import (
    CHARACTERS_DIR,
    MAX_SCALE,
    MIN_SCALE,
    ROOMS_DIR,
    AssetError,
    resolve_scale,
    select_character,
    select_room,
)
from piko.core.attention import AttentionCoordinator
from piko.core.config import ConfigStore
from piko.core.feature_base import FeatureContext, FeatureRegistry
from piko.core.logging_setup import setup_logging
from piko.core.settings_schema import FieldKind, SettingField, SettingsSection
from piko.core.ui_bus import UiBus
from piko.features.posture.feature import PostureFeature
from piko.features.stretch.feature import StretchFeature
from piko.ui import theme
from piko.ui.main_body import MainBody, PanelToggler
from piko.ui.piko_view import PikoView
from piko.ui.settings_dialog import SettingsDialog
from piko.ui.side_bar import SideBar, SideBarItem
from piko.ui.timer_panel import TimerPanel
from piko.ui.tray import Tray
from piko.ui.widget_window import WidgetWindow

APP_NAME = "Piko"
EXIT_ASSET_ERROR = 1
ASSET_ERROR_MESSAGE = (
    "그림 파일을 불러오지 못했습니다.\n{error}\n\n자세한 내용은 로그를 확인하세요."
)
AUTOSTART_ERROR_MESSAGE = "시작 프로그램 설정을 바꾸지 못했습니다.\n{error}"

# 외형 설정. None이면 자동(캐릭터/방은 폴더 이름 순 첫 번째, 배율은 방의 기본값)
APPEARANCE_SECTION = "appearance"
APPEARANCE_DEFAULTS: dict[str, Any] = {"character": None, "room": None, "scale": None}
APPEARANCE_SETTINGS = SettingsSection(
    APPEARANCE_SECTION,
    "화면",
    (
        SettingField(
            "scale", "확대 배율", FieldKind.INT, minimum=MIN_SCALE, maximum=MAX_SCALE, suffix=" 배"
        ),
    ),
)

# 창 위치. None이면 기본 위치(주 화면 우측 하단)
WINDOW_SECTION = "window"
WINDOW_DEFAULTS: dict[str, Any] = {"x": None, "y": None}

# 오른쪽 세로 메뉴바(위에서부터). 새 아이콘은 여기에 한 줄, 동작은 menu_actions에 추가한다
MENU_SETTINGS = "settings"
MENU_TIMER = "timer"
SIDE_BAR_ITEMS = (
    SideBarItem(MENU_SETTINGS, "설정"),
    SideBarItem(MENU_TIMER, "타이머", checkable=True),
)

logger = logging.getLogger(__name__)


def register_features(registry: FeatureRegistry) -> None:
    """사용할 기능을 등록한다. 새 기능은 여기에 한 줄 추가한다."""
    registry.register(PostureFeature)
    registry.register(StretchFeature)


def connect_bus(bus: UiBus, view: PikoView, tray: Tray) -> None:
    """기능의 요청을 실제 화면에, 화면의 알림을 기능에 연결한다."""
    bus.set_character_state.connect(view.set_override_state)
    bus.show_dialog.connect(view.show_message)
    bus.clear_dialog.connect(view.clear)
    bus.add_tray_action.connect(tray.add_action)
    bus.set_tray_action_text.connect(tray.set_action_text)
    view.button_clicked.connect(bus.dialog_button_clicked)
    tray.action_triggered.connect(bus.tray_action_triggered)


def saved_position(values: dict[str, Any]) -> QPoint | None:
    """설정에 저장된 창 위치. 없거나 잘못되었으면 None."""
    x, y = values.get("x"), values.get("y")
    if all(isinstance(v, int) and not isinstance(v, bool) for v in (x, y)):
        return QPoint(x, y)
    if (x, y) != (None, None):
        logger.warning("저장된 창 위치 (%r, %r)가 올바르지 않아 기본 위치를 씁니다", x, y)
    return None


class SettingsController:
    """설정 창을 띄우고 결과를 화면·기능·설정 파일에 반영한다."""

    def __init__(
        self,
        config: ConfigStore,
        registry: FeatureRegistry,
        window: WidgetWindow,
        view: PikoView,
    ) -> None:
        self._config = config
        self._registry = registry
        self._window = window
        self._view = view
        self._dialog: SettingsDialog | None = None

    def save_position(self, position: QPoint) -> None:
        """창 위치를 바로 저장한다."""
        self._config.set_section(WINDOW_SECTION, {"x": position.x(), "y": position.y()})
        self._config.save()

    def open(self) -> None:
        """설정 창을 연다. 이미 열려 있으면 앞으로 가져온다.

        모달이 아니라서 열려 있는 동안에도 위젯(메뉴바, 타이머 패널)을 쓸 수 있다.
        """
        if self._dialog is not None:
            self._dialog.raise_()
            return
        sections = [(APPEARANCE_SETTINGS, {"scale": self._view.scale})]
        sections += self._registry.settings_sections()
        dialog = SettingsDialog(sections)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.accepted.connect(lambda: self._apply(dialog.values(), dict(sections)))
        dialog.finished.connect(self._on_closed)
        dialog.place_near(self._window.frameGeometry())
        self._dialog = dialog
        dialog.show()

    def _on_closed(self) -> None:
        if self._dialog is not None:
            self._dialog.deleteLater()
        self._dialog = None

    def _apply(
        self,
        values: dict[str, dict[str, Any]],
        before: dict[SettingsSection, dict[str, Any]],
    ) -> None:
        for section, old_values in before.items():
            new_values = values[section.name]
            if new_values == {k: old_values.get(k) for k in new_values}:
                continue
            if section is APPEARANCE_SETTINGS:
                self._apply_scale(new_values["scale"])
            else:
                self._registry.apply_settings(section.name, new_values)
        self._config.save()

    def _apply_scale(self, scale: int) -> None:
        position = self._window.refit_keeping_bottom_right(lambda: self._view.set_scale(scale))
        appearance = self._config.section(APPEARANCE_SECTION, APPEARANCE_DEFAULTS)
        appearance["scale"] = scale
        self._config.set_section(APPEARANCE_SECTION, appearance)
        self._config.set_section(WINDOW_SECTION, {"x": position.x(), "y": position.y()})
        logger.info("배율 변경: %d", scale)


def sync_autostart(tray: Tray) -> None:
    """시작할 때 자동 실행 상태를 트레이에 반영한다.

    예전 레지스트리 등록은 바로가기로 옮기고, 실행 파일을 옮겼으면 바로가기를 고친다.
    """
    try:
        link = autostart.launch_shortcut()
        if not autostart.migrate_legacy(link):
            autostart.refresh_if_moved(link)
        tray.set_autostart_checked(autostart.is_enabled())
    except OSError:
        logger.exception("자동 실행 상태를 읽지 못했습니다")


def set_autostart(tray: Tray, enabled: bool) -> None:
    """트레이에서 자동 실행을 켜거나 끈다. 실패하면 알리고 체크를 실제 상태로 되돌린다."""
    try:
        if enabled:
            autostart.enable(autostart.launch_shortcut())
        else:
            autostart.disable()
    except OSError as exc:
        logger.exception("자동 실행 설정 실패")
        QMessageBox.warning(None, APP_NAME, AUTOSTART_ERROR_MESSAGE.format(error=exc))
    sync_autostart(tray)


def run(argv: list[str]) -> int:
    """앱을 실행하고 종료 코드를 반환한다."""
    setup_logging(paths.logs_dir())
    logger.info("피코 %s 시작", __version__)

    config = ConfigStore(paths.config_path())
    config.load()
    appearance = config.section(APPEARANCE_SECTION, APPEARANCE_DEFAULTS)
    config.set_section(APPEARANCE_SECTION, appearance)  # 설정 파일에 키가 보이게 한다
    window_values = config.section(WINDOW_SECTION, WINDOW_DEFAULTS)

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    theme.load_fonts()
    app.setFont(theme.ui_font())  # 모든 UI(트레이 메뉴 포함)의 기본 글꼴
    # 위젯을 숨겨도 앱은 트레이에 남는다. 종료는 트레이 메뉴로만 한다.
    app.setQuitOnLastWindowClosed(False)

    try:
        room = select_room(paths.asset_path(ROOMS_DIR), appearance["room"])
        character = select_character(paths.asset_path(CHARACTERS_DIR), appearance["character"])
        scale = resolve_scale(appearance["scale"], room.default_scale)
        view = PikoView(room, character, scale)
    except AssetError as exc:
        logger.exception("그림을 불러오지 못해 종료합니다")
        QMessageBox.critical(None, APP_NAME, ASSET_ERROR_MESSAGE.format(error=exc))
        return EXIT_ASSET_ERROR
    logger.info("방 '%s', 캐릭터 '%s', 배율 %d", room.id, character.id, scale)

    tray = Tray()
    bus = UiBus()
    connect_bus(bus, view, tray)
    registry = FeatureRegistry(config, FeatureContext(bus, AttentionCoordinator()))

    side_bar = SideBar(SIDE_BAR_ITEMS)
    body = MainBody(view, side_bar, TimerPanel(registry.timer_entries))
    window = WidgetWindow()
    window.setWindowTitle(APP_NAME)
    window.add_content(body)
    window.place(saved_position(window_values))

    register_features(registry)
    registry.start_all()
    settings = SettingsController(config, registry, window, view)
    panel = PanelToggler(window, body, MENU_TIMER)
    menu_actions = {MENU_SETTINGS: settings.open, MENU_TIMER: panel.toggle}
    side_bar.item_clicked.connect(lambda item_id: menu_actions[item_id]())

    def toggle_window() -> None:
        window.setVisible(not window.isVisible())
        tray.set_widget_visible(window.isVisible())

    tray.toggle_visibility_requested.connect(toggle_window)
    tray.settings_requested.connect(settings.open)
    tray.autostart_toggled.connect(lambda enabled: set_autostart(tray, enabled))
    sync_autostart(tray)
    tray.quit_requested.connect(app.quit)
    window.moved.connect(settings.save_position)
    window.moved.connect(lambda _pos: panel.forget_restore())

    window.show()
    tray.show()

    exit_code = app.exec()

    tray.hide()
    registry.stop_all()
    config.save()
    logger.info("피코 종료(코드 %d)", exit_code)
    return exit_code
