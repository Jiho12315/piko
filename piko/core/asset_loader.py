"""캐릭터/방 폴더와 JSON을 읽고 검증한다. Qt를 쓰지 않아 단위 테스트가 쉽다."""

import json
import logging
import re
import struct
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHARACTERS_DIR = "characters"
ROOMS_DIR = "rooms"
CHARACTER_FILE = "character.json"
ROOM_FILE = "room.json"
BACKGROUND_FILE = "background.png"
FRAME_GLOB = "*.png"
JSON_ENCODING = "utf-8"

# 코드가 직접 쓰는 상태. 그 밖의 상태는 폴더만 추가하면 인식된다.
STATE_IDLE = "idle"
STATE_WALK = "walk"
STATE_ALERT = "alert"
REQUIRED_STATES = (STATE_IDLE, STATE_WALK, STATE_ALERT)
# 방향별 폴더: <상태>_left / <상태>_right. 없는 쪽은 있는 쪽을 좌우 반전해서 쓴다.
LEFT_SUFFIX = "_left"
RIGHT_SUFFIX = "_right"
DEFAULT_FPS = 2.0
MIN_SCALE = 1
MAX_SCALE = 8

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_HEADER_LEN = 24
PNG_IHDR = b"IHDR"
_DIGITS = re.compile(r"(\d+)")


class AssetError(Exception):
    """그림 폴더나 JSON이 규격에 맞지 않음."""


@dataclass(frozen=True)
class CharacterSpec:
    """character.json과 상태별 프레임 파일. 좌표와 크기는 원본 픽셀 기준."""

    id: str
    name: str
    directory: Path
    frame_size: tuple[int, int]
    anchor: tuple[int, int]  # 발끝 기준점. 이 점이 방의 바닥선 위에 놓인다
    icon_anchor: tuple[int, int]  # 머리 위 아이콘 기준점(나중에 사용)
    walk_speed: float  # 초당 원본 픽셀
    fps: dict[str, float]  # 폴더 이름별 FPS
    frames: dict[str, list[Path]]  # 폴더 이름별 프레임(idle, walk_right, …)
    front_facing_states: frozenset[str] = frozenset()  # 정면 그림이라 좌우 반전하지 않는 상태

    @property
    def states(self) -> set[str]:
        """사용할 수 있는 상태 이름(방향 접미사를 뗀 이름)."""
        return {base_state(folder) for folder in self.frames}

    def first_available(self, candidates: str | list[str] | tuple[str, ...]) -> str | None:
        """후보 상태 중 이 캐릭터에 있는 첫 번째. 없으면 None."""
        if isinstance(candidates, str):
            candidates = [candidates]
        states = self.states
        return next((state for state in candidates if state in states), None)

    def frame_source(self, state: str, facing_right: bool) -> tuple[str, bool]:
        """상태와 보는 방향에 맞는 (프레임 폴더, 좌우 반전 여부).

        방향 폴더가 있으면 그것을, 반대쪽만 있으면 반전해서 쓴다. 방향 없는 폴더는 오른쪽을
        보는 그림으로 보고 왼쪽일 때 반전한다(정면 상태는 반전하지 않는다).
        """
        right, left = state + RIGHT_SUFFIX, state + LEFT_SUFFIX
        same, other = (right, left) if facing_right else (left, right)
        if same in self.frames:
            return same, False
        if other in self.frames:
            return other, True
        if state not in self.frames:
            raise ValueError(f"'{self.id}'에 없는 상태: {state}")
        return state, not facing_right and state not in self.front_facing_states


def base_state(folder: str) -> str:
    """폴더 이름에서 방향 접미사를 뗀 상태 이름. 예: walk_left → walk."""
    for suffix in (LEFT_SUFFIX, RIGHT_SUFFIX):
        if folder.endswith(suffix):
            return folder[: -len(suffix)]
    return folder


@dataclass(frozen=True)
class RoomSpec:
    """room.json과 배경 파일. 좌표와 크기는 원본 픽셀 기준."""

    id: str
    name: str
    directory: Path
    size: tuple[int, int]
    floor_y: int
    walk_range: tuple[int, int]  # 캐릭터 기준점 x의 이동 범위
    default_scale: int
    background: Path
    layers: list[Any] = field(default_factory=list)  # 나중에: 가구 레이어
    spots: list[Any] = field(default_factory=list)  # 나중에: 상호작용 지점


def _natural_key(path: Path) -> list[int | str]:
    """2.png가 10.png보다 앞에 오도록 숫자는 숫자로 비교한다."""
    return [int(part) if part.isdigit() else part.lower() for part in _DIGITS.split(path.name)]


def list_frame_files(directory: Path) -> list[Path]:
    """폴더 안 PNG를 이름 순(숫자는 자연 정렬)으로 반환한다. 폴더가 없으면 빈 목록."""
    if not directory.is_dir():
        return []
    return sorted(directory.glob(FRAME_GLOB), key=_natural_key)


def png_size(path: Path) -> tuple[int, int]:
    """PNG 헤더만 읽어 (너비, 높이)를 반환한다."""
    try:
        with path.open("rb") as file:
            header = file.read(PNG_HEADER_LEN)
    except OSError as exc:
        raise AssetError(f"PNG를 열 수 없음: {path} ({exc})") from exc
    if (
        len(header) < PNG_HEADER_LEN
        or not header.startswith(PNG_SIGNATURE)
        or header[12:16] != PNG_IHDR
    ):
        raise AssetError(f"PNG 형식이 아님: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def resolve_scale(value: Any, default: int) -> int:
    """설정의 배율을 검증한다. 비어 있거나 잘못되면 기본값을 쓴다."""
    if value is None:
        return default
    if isinstance(value, int) and not isinstance(value, bool) and MIN_SCALE <= value <= MAX_SCALE:
        return value
    logger.warning("배율 %r이(가) 올바르지 않아 %d를 씁니다", value, default)
    return default


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding=JSON_ENCODING))
    except FileNotFoundError as exc:
        raise AssetError(f"파일 없음: {path}") from exc
    except (OSError, ValueError) as exc:
        raise AssetError(f"JSON을 읽을 수 없음: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise AssetError(f"JSON 최상위가 객체가 아님: {path}")
    return data


def _require(data: dict[str, Any], key: str, path: Path) -> Any:
    if key not in data:
        raise AssetError(f"'{key}' 항목 없음: {path}")
    return data[key]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _int_pair(data: dict[str, Any], key: str, path: Path) -> tuple[int, int]:
    value = _require(data, key, path)
    if not isinstance(value, list) or len(value) != 2 or not all(_is_int(v) for v in value):
        raise AssetError(f"'{key}'는 정수 2개 목록이어야 함: {path}")
    return value[0], value[1]


def _positive_number(value: Any, key: str, path: Path) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise AssetError(f"'{key}'는 0보다 큰 숫자여야 함: {path}")
    return float(value)


def _list_or_empty(data: dict[str, Any], key: str, path: Path) -> list[Any]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise AssetError(f"'{key}'는 목록이어야 함: {path}")
    return value


def load_character(directory: Path) -> CharacterSpec:
    """캐릭터 폴더를 읽고 검증한다. 규격에 맞지 않으면 AssetError."""
    path = directory / CHARACTER_FILE
    data = _read_json(path)

    frame_size = _int_pair(data, "frame_size", path)
    if min(frame_size) <= 0:
        raise AssetError(f"'frame_size'는 0보다 커야 함: {path}")
    anchor = _int_pair(data, "anchor", path)
    icon_anchor = _int_pair(data, "icon_anchor", path)
    for key, (x, y) in (("anchor", anchor), ("icon_anchor", icon_anchor)):
        if not (0 <= x <= frame_size[0] and 0 <= y <= frame_size[1]):
            raise AssetError(f"'{key}'가 프레임 밖에 있음: {path}")
    walk_speed = _positive_number(_require(data, "walk_speed", path), "walk_speed", path)
    raw_fps = data.get("fps", {})
    if not isinstance(raw_fps, dict):
        raise AssetError(f"'fps'는 객체여야 함: {path}")
    front_facing = data.get("front_facing_states", [])
    if not isinstance(front_facing, list) or not all(isinstance(s, str) for s in front_facing):
        raise AssetError(f"'front_facing_states'는 문자열 목록이어야 함: {path}")

    frames: dict[str, list[Path]] = {}
    for state_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
        files = list_frame_files(state_dir)
        if files:
            frames[state_dir.name] = files
    available = {base_state(folder) for folder in frames}
    missing = [state for state in REQUIRED_STATES if state not in available]
    if missing:
        raise AssetError(f"프레임이 없는 상태 {missing}: {directory}")
    for files in frames.values():
        for file in files:
            size = png_size(file)
            if size != frame_size:
                raise AssetError(f"프레임 크기 {size}가 frame_size {frame_size}와 다름: {file}")

    # 방향 폴더(walk_left)는 자기 값이 없으면 상태(walk)의 FPS를 쓴다
    fps = {
        folder: _positive_number(
            raw_fps.get(folder, raw_fps.get(base_state(folder), DEFAULT_FPS)),
            f"fps.{folder}",
            path,
        )
        for folder in frames
    }
    return CharacterSpec(
        id=directory.name,
        name=str(data.get("name", directory.name)),
        directory=directory,
        frame_size=frame_size,
        anchor=anchor,
        icon_anchor=icon_anchor,
        walk_speed=walk_speed,
        fps=fps,
        frames=frames,
        front_facing_states=frozenset(front_facing),
    )


def load_room(directory: Path) -> RoomSpec:
    """방 폴더를 읽고 검증한다. 규격에 맞지 않으면 AssetError."""
    path = directory / ROOM_FILE
    data = _read_json(path)

    size = _int_pair(data, "size", path)
    if min(size) <= 0:
        raise AssetError(f"'size'는 0보다 커야 함: {path}")
    floor_y = _require(data, "floor_y", path)
    if not _is_int(floor_y) or not 0 < floor_y <= size[1]:
        raise AssetError(f"'floor_y'는 1~{size[1]} 사이 정수여야 함: {path}")
    low, high = _int_pair(data, "walk_range", path)
    if not 0 <= low < high <= size[0]:
        raise AssetError(f"'walk_range'는 0 이상 {size[0]} 이하의 [작은 값, 큰 값]: {path}")
    default_scale = _require(data, "default_scale", path)
    if not _is_int(default_scale) or not MIN_SCALE <= default_scale <= MAX_SCALE:
        raise AssetError(f"'default_scale'은 {MIN_SCALE}~{MAX_SCALE} 정수여야 함: {path}")

    background = directory / BACKGROUND_FILE
    if not background.is_file():
        raise AssetError(f"배경 그림 없음: {background}")
    bg_size = png_size(background)
    if bg_size != size:
        raise AssetError(f"배경 크기 {bg_size}가 size {size}와 다름: {background}")

    return RoomSpec(
        id=directory.name,
        name=str(data.get("name", directory.name)),
        directory=directory,
        size=size,
        floor_y=floor_y,
        walk_range=(low, high),
        default_scale=default_scale,
        background=background,
        layers=_list_or_empty(data, "layers", path),
        spots=_list_or_empty(data, "spots", path),
    )


def _select[T](parent: Path, preferred: str | None, loader: Callable[[Path], T], kind: str) -> T:
    """preferred를 먼저 시도하고, 안 되면 나머지 폴더를 이름 순으로 시도한다."""
    candidates = sorted(p.name for p in parent.iterdir() if p.is_dir()) if parent.is_dir() else []
    order = ([preferred] if preferred else []) + [c for c in candidates if c != preferred]
    for item_id in order:
        try:
            spec = loader(parent / item_id)
        except AssetError as exc:
            logger.warning("%s '%s'을(를) 쓸 수 없음: %s", kind, item_id, exc)
            continue
        if preferred and item_id != preferred:
            logger.warning("%s '%s' 대신 '%s'을(를) 사용합니다", kind, preferred, item_id)
        return spec
    raise AssetError(f"사용할 수 있는 {kind}이(가) 없음: {parent}")


def select_character(parent: Path, preferred: str | None) -> CharacterSpec:
    """설정에서 고른 캐릭터를 읽는다. 안 되면 다른 캐릭터로 대체한다."""
    return _select(parent, preferred, load_character, "캐릭터")


def select_room(parent: Path, preferred: str | None) -> RoomSpec:
    """설정에서 고른 방을 읽는다. 안 되면 다른 방으로 대체한다."""
    return _select(parent, preferred, load_room, "방")
