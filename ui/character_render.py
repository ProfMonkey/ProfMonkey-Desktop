"""QtSvg rasterization of the six original v0.20 SVG characters.

Runs once per unseen animation frame then reuses MonkeyOverlay's QPixmap cache.
QtSvg ships with PySide6; no external font, file server or runtime artwork
generation process is needed.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from core.character_art import pose_svg


def render_mascot(asset_root: Path, personality: str, action: str = 'idle',
                  frame: int = 0, frame_count: int = 1,
                  skin: str = 'professor') -> QPixmap:
    if skin == 'pixel':
        # Pixelorama-importable 3x2 spritesheet; each transparent cell is 64x64.
        from core.character_art import CHARACTERS
        sprite_path = Path(asset_root).parent / 'pixelorama_v021' / 'monkey_spritesheet_3x2.png'
        sheet = QPixmap(str(sprite_path))
        if sheet.isNull() or sheet.width() != 192 or sheet.height() != 128:
            raise ValueError('Pixel art spritesheet missing or invalid: ' + str(sprite_path))
        positions = {
            'trickster': (0, 0), 'shy': (1, 0), 'scholar': (2, 0),
            'sleepy': (0, 1), 'inventor': (1, 1), 'captain': (2, 1),
        }
        if personality not in CHARACTERS or personality not in positions:
            raise ValueError('unknown pixel-art mascot personality')
        col, row = positions[personality]
        cel = sheet.copy(col * 64, row * 64, 64, 64)
        return cel.scaled(256, 256, Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.FastTransformation)
    svg = pose_svg(asset_root, personality, action, frame, frame_count)
    renderer = QSvgRenderer(QByteArray(svg))
    if not renderer.isValid():
        raise ValueError('invalid packaged monkey character SVG')
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    if pixmap.isNull():
        raise ValueError('unable to draw packaged monkey character')
    return pixmap
