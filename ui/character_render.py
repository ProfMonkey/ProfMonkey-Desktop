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
                  frame: int = 0, frame_count: int = 1) -> QPixmap:
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
