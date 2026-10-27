"""Pillow-compatible, screen-free rasterization of six bundled SVG mascots.

CairoSVG is optional for development; the installed PySide6 QtSvg renderer
supports Windows runtime fallback. Neither path captures the user's desktop.
"""
from __future__ import annotations
import io
from pathlib import Path
from PIL import Image
from core.character_art import pose_svg


def raster_mascot(asset_root: Path, personality: str, action: str = 'idle',
                  frame: int = 0, frame_count: int = 1, size: int = 256) -> Image.Image:
    if type(size) is not int or not 32 <= size <= 1024:
        raise ValueError('invalid mascot raster size')
    data = pose_svg(Path(asset_root), personality, action, frame, frame_count)
    try:
        import cairosvg
    except ImportError:
        # QtSvg is present whenever the real desktop program can run.
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
        renderer = QSvgRenderer(QByteArray(data))
        if not renderer.isValid():
            raise ValueError('invalid original monkey SVG')
        image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        try:
            renderer.render(painter)
        finally:
            painter.end()
        raw = QByteArray()
        buffer = QBuffer(raw)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        try:
            if not image.save(buffer, 'PNG'):
                raise ValueError('unable to render monkey mascot')
        finally:
            buffer.close()
        png = bytes(raw)
    else:
        png = cairosvg.svg2png(bytestring=data, output_width=size, output_height=size)
    with Image.open(io.BytesIO(png)) as result:
        return result.convert('RGBA')
