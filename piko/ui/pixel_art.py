"""도트 그림 읽기: 정수 배율로 보간 없이(nearest-neighbor) 확대한다."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from piko.core.asset_loader import AssetError


def load_pixel_image(path: Path, scale: int) -> QImage:
    """PNG를 읽어 scale배로 확대한다. 읽을 수 없으면 AssetError."""
    image = QImage(str(path))
    if image.isNull():
        raise AssetError(f"이미지를 읽을 수 없음: {path}")
    return image.scaled(
        image.width() * scale,
        image.height() * scale,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
