"""Optional Windows/offscreen smoke test requiring full binary artwork and PySide6."""
import os
from pathlib import Path
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from core.config import Settings
from core.relationships import RelationshipStore
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony


def test_selected_pair_creates_two_beat_scene_and_cancellation_has_no_effects(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    sprite = root / 'assets/monkey/idle.png'
    manifest = root / 'assets/monkey/manifest.json'
    if not sprite.is_file():
        pytest.skip('requires recovered original binary artwork')
    settings = Settings(monkey_count=2, monkey_profiles=[
        {'name': '队长', 'personality': 'captain'},
        {'name': '困困', 'personality': 'sleepy'},
    ]).validated()
    primary = MonkeyOverlay(sprite, manifest, settings=settings)
    colony = MonkeyColony(primary, sprite, manifest)
    colony.relationships = RelationshipStore(tmp_path / 'relationships.json')
    try:
        primary.show()
        colony.set_count(2)
        assert not colony.demo_pair(0, 0)
        assert colony.demo_pair(0, 1)
        assert colony.duo.active
        assert colony.duo.event.kind == 'roll_call'
        assert all(p._social_active for p in colony.monkeys)
        assert not colony.demo_pair(0, 1)  # no overlapping mini-stories
        colony.toggle_pause(True)
        assert not colony.duo.active
        assert not any(p._social_active for p in colony.monkeys)
        assert colony.relationships.get(0, 1)['interactions'] == 0
    finally:
        colony.quit_all()
