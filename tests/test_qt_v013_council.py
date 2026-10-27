"""Optional integrated Qt smoke: council controls real distinct pet windows."""
import os
from pathlib import Path

import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from core.relationships import RelationshipStore
from ui.colony import MonkeyColony
from ui.council_dialog import CouncilDialog
from ui.overlay import MonkeyOverlay


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    instance = QApplication.instance() or QApplication([])
    yield instance
    instance.processEvents()


def make_colony(root, tmp_path):
    picture = root/'assets/monkey/idle.png'
    manifest = root/'assets/monkey/manifest.json'
    if not picture.is_file():
        pytest.skip('original v0.9 binary assets not restored')
    profiles = [
        {'name':'学究猴','personality':'scholar'},
        {'name':'队长猴','personality':'captain'},
        {'name':'困猴','personality':'sleepy'}]
    primary = MonkeyOverlay(picture, manifest, settings=Settings(
        monkey_count=3, monkey_profiles=profiles).validated())
    colony = MonkeyColony(primary, picture, manifest)
    colony.relationships = RelationshipStore(tmp_path/'relationships.json')
    primary.show()
    colony.set_count(3)
    return colony


def test_council_requires_full_three_beat_completion_and_cancel(tmp_path, app):
    root=Path(__file__).resolve().parents[1]
    colony=make_colony(root, tmp_path)
    try:
        assert not colony.start_council('quiet_hours',(0,1))
        assert not colony.start_council('quiet_hours',(0,0,1))
        assert colony.start_council('quiet_hours',(0,1,2))
        assert colony.council.active
        assert all(p._social_active for p in colony.monkeys)
        assert not colony.start_social('meeting')
        assert not colony.demo_pair(0,1)
        assert not colony.drop_shared_banana()
        colony._complete_council()  # must not commit before the final beat
        assert not (tmp_path/'relationships.json').exists()
        colony.toggle_pause(True)
        assert not colony.council.active
        assert not any(p._social_active for p in colony.monkeys)
        assert not (tmp_path/'relationships.json').exists()
        colony.toggle_pause(False)
        assert colony.start_council('quiet_hours',(0,1,2))
        while not colony.council.finished:
            colony.council.advance(.4)
        colony._complete_council()
        colony._complete_council()  # duplicate completion must be idempotent
        assert colony.relationships.get(0,1)['interactions'] == 1
        colony.cancel_council()
        assert not any(p._social_active for p in colony.monkeys)
    finally:
        colony.quit_all()


def test_council_binds_actual_selection_and_rejects_missing_member(tmp_path, app):
    root=Path(__file__).resolve().parents[1]
    colony=make_colony(root, tmp_path)
    try:
        dlg=CouncilDialog(colony)
        assert len(dlg.checks) == 3
        assert dlg.selected() == (0,1,2)
        assert dlg.start_button.isEnabled()
        dlg.checks[2].setChecked(False)
        assert not dlg.start_button.isEnabled()
        dlg.checks[2].setChecked(True)
        assert dlg.start_button.isEnabled()
        dlg.close()
        assert colony.start_council('banana_rules',(0,1,2))
        colony.hide_all()
        assert not colony.council.active
        colony.show_all()
        colony.set_count(1)
        assert not colony.start_council('banana_rules',(0,1,2))
    finally:
        colony.quit_all()
