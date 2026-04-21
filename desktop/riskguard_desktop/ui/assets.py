from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPixmap


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def riskguard_icon_path() -> str:
    desktop_local = project_root() / "desktop" / "assets" / "guard.png"
    if desktop_local.exists():
        return str(desktop_local)
    desktop_custom = Path(r"D:\guard.png")
    if desktop_custom.exists():
        return str(desktop_custom)
    icon_path = project_root() / "web" / "static" / "riskguard-icon.png"
    return str(icon_path)


def _trim_transparent_padding(image: QImage) -> QImage:
    if image.isNull() or not image.hasAlphaChannel():
        return image

    width = image.width()
    height = image.height()
    left = width
    right = -1
    top = height
    bottom = -1

    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() > 0:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

    if right < left or bottom < top:
        return image
    return image.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def load_app_icon(size: int = 44) -> QPixmap:
    pixmap = QPixmap(riskguard_icon_path())
    if pixmap.isNull():
        return QPixmap()
    trimmed = _trim_transparent_padding(pixmap.toImage())
    result = QPixmap.fromImage(trimmed)
    return result.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
