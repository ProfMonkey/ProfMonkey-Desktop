"""Optional Qt integration smoke test (run on Windows before release)."""
import os
import pathlib
import pytest

qt = pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    return QApplication.instance() or QApplication([])


def test_count_change_creates_real_independent_qt_windows(app):
    root = pathlib.Path(__file__).parents[1]
    image, manifest = root / 'assets/monkey/idle.png', root / 'assets/monkey/manifest.json'
    primary = MonkeyOverlay(image, manifest, settings=Settings())
    colony = MonkeyColony(primary, image, manifest)
    try:
        colony.set_count(3)
        assert len(colony.monkeys) == 3
        assert len(set(map(id, colony.monkeys))) == 3
        assert len(set(map(id, (p.player for p in colony.monkeys)))) == 3
        assert len(set(map(id, (p.body for p in colony.monkeys)))) == 3
        assert len(set(map(id, (p.brain for p in colony.monkeys)))) == 3
        assert all(p.focus is primary.focus for p in colony.monkeys)
        colony.monkeys[1].stats.tap()
        assert colony.monkeys[0].stats.mood == 15
        colony.set_count(2)
        assert colony.count == 2
        colony.set_count(6)
        assert colony.count == 6
        colony.toggle_pause(True)
        assert all(p.paused for p in colony.monkeys)
        colony.toggle_pause(False)
        assert not any(p.paused for p in colony.monkeys)
        colony.set_count(1)
        assert colony.monkeys == [primary]
    finally:
        colony.quit_all()
