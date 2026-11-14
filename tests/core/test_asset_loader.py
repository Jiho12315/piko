"""캐릭터/방 폴더 읽기와 검증 테스트."""

import json
import logging
import struct
import zlib
from pathlib import Path
from typing import Any

import pytest

from piko.core.asset_loader import (
    MAX_SCALE,
    AssetError,
    list_frame_files,
    load_character,
    load_room,
    png_size,
    resolve_scale,
    select_character,
    select_room,
)

STATES = ("idle", "walk", "alert")


def write_png(path: Path, width: int, height: int) -> None:
    """투명한 width x height PNG를 쓴다(Qt 없이)."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + b"\x00" * (width * 4) for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def make_character(
    parent: Path, char_id: str, size: tuple[int, int] = (32, 64), **override: Any
) -> Path:
    directory = parent / char_id
    spec: dict[str, Any] = {
        "name": char_id,
        "frame_size": list(size),
        "anchor": [size[0] // 2, size[1] - 2],
        "icon_anchor": [size[0] // 2, 2],
        "walk_speed": 20,
        "fps": {"idle": 2, "walk": 4},
    }
    spec.update(override)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "character.json").write_text(json.dumps(spec), encoding="utf-8")
    for state in STATES:
        for i in (1, 2):
            write_png(directory / state / f"{i:04d}.png", *size)
    return directory


def make_room(parent: Path, room_id: str, **override: Any) -> Path:
    directory = parent / room_id
    spec: dict[str, Any] = {
        "name": room_id,
        "size": [192, 96],
        "floor_y": 88,
        "walk_range": [20, 172],
        "default_scale": 3,
        "layers": [],
        "spots": [],
    }
    spec.update(override)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "room.json").write_text(json.dumps(spec), encoding="utf-8")
    write_png(directory / "background.png", 192, 96)
    return directory


# --- 공통 ---


def test_list_frame_files_natural_order_and_png_only(tmp_path: Path) -> None:
    for name in ["10.png", "2.png", "1.png", "notes.txt"]:
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in list_frame_files(tmp_path)] == ["1.png", "2.png", "10.png"]
    assert list_frame_files(tmp_path / "없음") == []


def test_png_size_reads_header(tmp_path: Path) -> None:
    write_png(tmp_path / "a.png", 40, 24)
    assert png_size(tmp_path / "a.png") == (40, 24)


def test_png_size_rejects_non_png(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"not a png at all, just text....")
    with pytest.raises(AssetError):
        png_size(tmp_path / "a.png")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, 3), (2, 2), (MAX_SCALE, MAX_SCALE), (0, 3), (MAX_SCALE + 1, 3), ("2", 3), (True, 3)],
)
def test_resolve_scale(value: Any, expected: int) -> None:
    assert resolve_scale(value, 3) == expected


# --- 캐릭터 ---


def test_load_character_reads_spec_and_frames(tmp_path: Path) -> None:
    spec = load_character(make_character(tmp_path, "c1"))
    assert spec.id == "c1"
    assert spec.frame_size == (32, 64)
    assert spec.anchor == (16, 62)
    assert set(spec.frames) == set(STATES)
    assert [p.name for p in spec.frames["idle"]] == ["0001.png", "0002.png"]
    # fps에 없는 상태는 기본값
    assert spec.fps["walk"] == 4.0 and spec.fps["alert"] > 0


def make_directional(tmp_path: Path, folders: tuple[str, ...], **override: Any) -> Path:
    """walk 대신 방향 폴더를 가진 캐릭터를 만든다."""
    directory = make_character(tmp_path, "d1", **override)
    for file in (directory / "walk").iterdir():
        file.unlink()
    (directory / "walk").rmdir()
    for folder in folders:
        for i in (1, 2, 3):
            write_png(directory / folder / f"{i:04d}.png", 32, 64)
    return directory


def test_directional_folders_satisfy_walk(tmp_path: Path) -> None:
    spec = load_character(make_directional(tmp_path, ("walk_left", "walk_right")))
    assert spec.states == {"idle", "walk", "alert"}
    assert len(spec.frames["walk_left"]) == 3
    # 방향 폴더는 자기 FPS가 없으면 walk의 FPS를 쓴다
    assert spec.fps["walk_left"] == spec.fps["walk_right"] == 4.0


def test_one_direction_only_is_enough(tmp_path: Path) -> None:
    spec = load_character(make_directional(tmp_path, ("walk_left",)))
    assert "walk" in spec.states


@pytest.mark.parametrize(
    ("folders", "facing_right", "expected"),
    [
        (("walk_left", "walk_right"), True, ("walk_right", False)),
        (("walk_left", "walk_right"), False, ("walk_left", False)),
        (("walk_right",), False, ("walk_right", True)),
        (("walk_left",), True, ("walk_left", True)),
        (("walk_left",), False, ("walk_left", False)),
    ],
)
def test_frame_source_directional(
    tmp_path: Path, folders: tuple[str, ...], facing_right: bool, expected: tuple[str, bool]
) -> None:
    spec = load_character(make_directional(tmp_path, folders))
    assert spec.frame_source("walk", facing_right) == expected


def test_frame_source_plain_folder_flips_unless_front_facing(tmp_path: Path) -> None:
    spec = load_character(make_character(tmp_path, "c1", front_facing_states=["idle"]))
    assert spec.frame_source("walk", True) == ("walk", False)
    assert spec.frame_source("walk", False) == ("walk", True)
    assert spec.frame_source("idle", False) == ("idle", False)  # 정면 그림은 반전하지 않음
    with pytest.raises(ValueError):
        spec.frame_source("sleep", True)


def test_first_available_picks_first_existing_state(tmp_path: Path) -> None:
    spec = load_character(make_directional(tmp_path, ("walk_right",)))
    assert spec.first_available(["stretch", "alert"]) == "alert"  # stretch 폴더 없음 → alert
    assert spec.first_available("walk") == "walk"
    assert spec.first_available(["sleep"]) is None
    write_png(spec.directory / "stretch" / "0001.png", 32, 64)
    assert load_character(spec.directory).first_available(["stretch", "alert"]) == "stretch"


def test_front_facing_states_must_be_string_list(tmp_path: Path) -> None:
    with pytest.raises(AssetError):
        load_character(make_character(tmp_path, "c1", front_facing_states="idle"))


def test_extra_state_folder_is_recognized(tmp_path: Path) -> None:
    directory = make_character(tmp_path, "c1")
    write_png(directory / "sleep" / "0001.png", 32, 64)
    assert "sleep" in load_character(directory).frames


def test_character_frame_size_mismatch(tmp_path: Path) -> None:
    directory = make_character(tmp_path, "c1")
    write_png(directory / "walk" / "0002.png", 30, 64)
    with pytest.raises(AssetError, match="프레임 크기"):
        load_character(directory)


def test_character_missing_state(tmp_path: Path) -> None:
    directory = make_character(tmp_path, "c1")
    for file in (directory / "alert").iterdir():
        file.unlink()
    with pytest.raises(AssetError, match="alert"):
        load_character(directory)


@pytest.mark.parametrize(
    "override",
    [
        {"frame_size": [32]},
        {"anchor": [99, 10]},
        {"walk_speed": 0},
        {"fps": {"idle": -1}},
        {"fps": [1, 2]},
    ],
)
def test_character_invalid_json_values(tmp_path: Path, override: dict[str, Any]) -> None:
    directory = make_character(tmp_path, "c1", **override)
    with pytest.raises(AssetError):
        load_character(directory)


def test_character_broken_json(tmp_path: Path) -> None:
    directory = make_character(tmp_path, "c1")
    (directory / "character.json").write_text("{ 깨짐", encoding="utf-8")
    with pytest.raises(AssetError):
        load_character(directory)


def test_select_character_preferred(tmp_path: Path) -> None:
    make_character(tmp_path, "a")
    make_character(tmp_path, "b", size=(40, 40))
    assert select_character(tmp_path, "b").frame_size == (40, 40)


def test_select_character_none_picks_first_by_name(tmp_path: Path) -> None:
    make_character(tmp_path, "b")
    make_character(tmp_path, "a")
    assert select_character(tmp_path, None).id == "a"


def test_select_character_falls_back_and_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    make_character(tmp_path, "good")
    broken = make_character(tmp_path, "broken")
    write_png(broken / "idle" / "0001.png", 1, 1)
    with caplog.at_level(logging.WARNING):
        assert select_character(tmp_path, "broken").id == "good"
    assert "broken" in caplog.text


def test_select_character_missing_preferred_falls_back(tmp_path: Path) -> None:
    make_character(tmp_path, "good")
    assert select_character(tmp_path, "없는캐릭터").id == "good"


def test_select_character_nothing_valid(tmp_path: Path) -> None:
    with pytest.raises(AssetError):
        select_character(tmp_path, None)


# --- 방 ---


def test_load_room_reads_spec(tmp_path: Path) -> None:
    room = load_room(make_room(tmp_path, "r1"))
    assert room.size == (192, 96)
    assert room.floor_y == 88
    assert room.walk_range == (20, 172)
    assert room.default_scale == 3
    assert room.layers == [] and room.spots == []


@pytest.mark.parametrize(
    "override",
    [
        {"floor_y": 0},
        {"floor_y": 97},
        {"walk_range": [100, 50]},
        {"walk_range": [0, 999]},
        {"default_scale": 0},
        {"size": [100, 96]},  # 배경 크기와 불일치
        {"layers": "x"},
    ],
)
def test_room_invalid_values(tmp_path: Path, override: dict[str, Any]) -> None:
    with pytest.raises(AssetError):
        load_room(make_room(tmp_path, "r1", **override))


def test_room_missing_background(tmp_path: Path) -> None:
    directory = make_room(tmp_path, "r1")
    (directory / "background.png").unlink()
    with pytest.raises(AssetError, match="배경"):
        load_room(directory)


def test_select_room_falls_back(tmp_path: Path) -> None:
    make_room(tmp_path, "good")
    make_room(tmp_path, "bad", floor_y=0)
    assert select_room(tmp_path, "bad").id == "good"
