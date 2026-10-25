"""Qt shape integrity; OS hit-test verification still needs a Windows desktop."""

import pytest

PySide6 = pytest.importorskip('PySide6')
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from ui.overlay import sprite_window_mask


def test_qt_shape_excludes_transparent_corners():
    app = QApplication.instance() or QApplication([])
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'assets/monkey/idle.png'
    sprite = QPixmap(str(path))
    mask = sprite_window_mask(sprite)
    assert not mask.contains(QPoint(0, 0))
    assert mask.contains(QPoint(125, 105))
    assert not mask.isEmpty()
    assert app is not None
