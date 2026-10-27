"""Optional Qt/offscreen integration gate for v0.12 story playback."""
import os
from pathlib import Path
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.chronicle import ChronicleStore
from core.config import Settings
from core.relationships import RelationshipStore
from ui.colony import MonkeyColony
from ui.overlay import MonkeyOverlay


def test_chronicle_chapter_requires_full_two_beat_playback(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    image, manifest = root / 'assets/monkey/idle.png', root / 'assets/monkey/manifest.json'
    if not image.is_file():
        pytest.skip('old v0.9 archive artwork not restored')
    settings = Settings(monkey_count=2, monkey_profiles=[
        {'name':'实验猴','personality':'scholar'},
        {'name':'发明猴','personality':'inventor'},
    ]).validated()
    primary = MonkeyOverlay(image, manifest, settings=settings)
    colony = MonkeyColony(primary, image, manifest)
    colony.relationships = RelationshipStore(tmp_path / 'relationships.json')
    colony.chronicle = ChronicleStore(tmp_path / 'chronicle.json', enabled=True)
    try:
        primary.show()
        colony.set_count(2)
        cid = colony.chronicle.observe('invention', 0, 1)
        assert cid == 1
        assert colony.play_chronicle_chapter(cid)
        assert colony._active_chapter is not None
        assert colony.duo.event.kind == 'chronicle'
        assert all(p._social_active for p in colony.monkeys)
        assert not colony.play_chronicle_chapter(cid)
        colony._complete_duo()  # must NOT award before final beat
        assert colony.chronicle.preview(cid).chapter == 0
        assert colony.chronicle.growth_for(0)['research'] == 0
        # Pausing clears the active scene and does not advance.
        colony.toggle_pause(True)
        assert not colony.duo.active and colony._active_chapter is None
        assert colony.chronicle.preview(cid).chapter == 0
        colony.toggle_pause(False)
        assert colony.play_chronicle_chapter(cid)
        while not colony.duo.finished:
            colony.duo.advance(.4)
        colony._complete_duo()
        colony.cancel_duo()
        assert colony.chronicle.preview(cid).chapter == 1
        assert colony.chronicle.growth_for(0)['research'] == 1
        assert colony.relationships.get(0, 1)['interactions'] == 1
        assert not any(p._social_active for p in colony.monkeys)
    finally:
        colony.quit_all()


def test_hidden_or_absent_monkey_cannot_play_pending_chapter(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    image, manifest = root / 'assets/monkey/idle.png', root / 'assets/monkey/manifest.json'
    if not image.is_file():
        pytest.skip('old v0.9 archive artwork not restored')
    primary = MonkeyOverlay(image, manifest, settings=Settings())
    colony = MonkeyColony(primary, image, manifest)
    colony.chronicle = ChronicleStore(tmp_path / 'chronicle.json', enabled=True)
    try:
        primary.show()
        colony.set_count(2)
        cid = colony.chronicle.observe('banana_duel', 0, 1)
        assert cid
        colony.hide_all()
        assert not colony.play_chronicle_chapter(cid)
        colony.show_all()
        colony.set_count(1)
        assert not colony.play_chronicle_chapter(cid)
        assert colony.chronicle.preview(cid).chapter == 0
    finally:
        colony.quit_all()
