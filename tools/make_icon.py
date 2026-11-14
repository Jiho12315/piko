"""캐릭터 첫 idle 프레임의 머리 부분으로 피코 아이콘(assets/ui/piko.ico)을 만든다.

캐릭터 그림을 바꾸면 다시 실행한다.
사용법: .\\.venv\\Scripts\\python.exe tools\\make_icon.py [캐릭터 폴더명]
ICO 안에 크기별 PNG를 넣는다. 큰 크기는 도트가 살도록 nearest, 작은 크기는 부드럽게 줄인다.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QBuffer, QIODevice, QRect, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

from piko.core import paths  # noqa: E402
from piko.core.asset_loader import CHARACTERS_DIR  # noqa: E402

DEFAULT_CHARACTER = "girl"
FRAME_PATH = ("idle", "0001.png")
BASE_SIZE = 64  # 머리 부분을 이 크기의 정사각형 가운데에 놓는다
SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_HEADER = "<HHH"  # reserved, type(1=icon), count
ICO_ENTRY = "<BBBBHHII"  # w, h, colors, reserved, planes, bpp, size, offset
ICO_TYPE_ICON = 1
ICO_PLANES = 1
ICO_BPP = 32
ICO_MAX_BYTE_SIZE = 256  # 256은 0으로 적는다


def head_image(frame: QImage) -> QImage:
    """프레임 위쪽(폭만큼의 정사각형)을 BASE_SIZE 투명 정사각형 가운데에 놓는다."""
    side = min(frame.width(), frame.height())
    head = frame.copy(QRect(0, 0, side, side))
    base = QImage(BASE_SIZE, BASE_SIZE, QImage.Format.Format_ARGB32)
    base.fill(Qt.GlobalColor.transparent)
    painter = QPainter(base)
    painter.drawImage((BASE_SIZE - side) // 2, (BASE_SIZE - side) // 2, head)
    painter.end()
    return base


def png_bytes(image: QImage) -> bytes:
    """QImage를 PNG 바이트로."""
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data().data())


def write_ico(base: QImage, path: Path) -> None:
    """크기별 PNG를 담은 ICO 파일을 쓴다."""
    images = []
    for size in SIZES:
        mode = (
            Qt.TransformationMode.FastTransformation
            if size >= BASE_SIZE
            else Qt.TransformationMode.SmoothTransformation
        )
        images.append((size, png_bytes(base.scaled(size, size, mode=mode))))
    header = struct.pack(ICO_HEADER, 0, ICO_TYPE_ICON, len(images))
    offset = len(header) + struct.calcsize(ICO_ENTRY) * len(images)
    entries = b""
    for size, data in images:
        byte_size = 0 if size >= ICO_MAX_BYTE_SIZE else size
        entries += struct.pack(
            ICO_ENTRY, byte_size, byte_size, 0, 0, ICO_PLANES, ICO_BPP, len(data), offset
        )
        offset += len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + entries + b"".join(data for _, data in images))


def main() -> None:
    """아이콘을 만든다."""
    character = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CHARACTER
    QGuiApplication([])
    frame = QImage(str(paths.asset_path(CHARACTERS_DIR, character, *FRAME_PATH)))
    if frame.isNull():
        raise SystemExit(f"프레임을 읽지 못함: {character}/{'/'.join(FRAME_PATH)}")
    target = paths.app_icon_path()
    write_ico(head_image(frame), target)
    print(f"아이콘 생성: {target}")  # noqa: T201 (명령줄 도구 출력)


if __name__ == "__main__":
    main()
