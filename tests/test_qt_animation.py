"""Qt-render-path smoke checks; skips if platform plugin/PySide6 unavailable."""

import pytest

PySide6 = pytest.importorskip('PySide6')
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from ui.overlay import MonkeyOverlay


def test_p02_frame_and_mask_smoke():
    from pathlib import Path
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1] / 'assets/monkey'
    overlay = MonkeyOverlay(root / 'idle.png', root / 'manifest.json')
    overlay._timer.stop()
    for action in ('idle', 'blink', 'walk', 'turn', 'sleep', 'wake', 'fall', 'get_up'):
        overlay.play_action(action)
        assert isinstance(overlay._sprite, QPixmap)
        assert not overlay._sprite.isNull()
        assert not overlay._hit_region.isEmpty()
    assert not overlay._missing_frames
    overlay.close()
    assert app
