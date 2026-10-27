"""Optional manual Qt smoke for v0.18; no art or GitHub Actions needed."""
import os
from types import SimpleNamespace
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.expeditions import ExpeditionJournal
from core.city_life import prepare_city_case
from core.relationships import RelationshipStore
from ui.evolution_dialog import EvolutionDialog


@pytest.fixture
def app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    instance = QApplication.instance() or QApplication([])
    yield instance


def make_dialog(tmp_path):
    journal = ExpeditionJournal(tmp_path / 'expeditions.json')
    journal.resources.update(bananas=80, science=80, reputation=80)
    assert journal.construct('banana_vault')
    for _ in range(3):
        plan = prepare_city_case('banana_vault', journal.city_cases['banana_vault'],
                                 0, 1, 'careful')
        assert journal.record_city_chapter(plan)
    bonds = RelationshipStore(tmp_path / 'relationships.json')
    colony = SimpleNamespace(
        expeditions=journal, laws=None, relationships=bonds, count=2,
        monkeys=[SimpleNamespace(display_name='学究猴'),
                 SimpleNamespace(display_name='皮猴')])
    return EvolutionDialog(colony), colony


def test_three_scene_finish_only_after_user_confirms(tmp_path, app):
    dialog, colony = make_dialog(tmp_path)
    try:
        assert dialog.advance.isEnabled()
        before = dict(colony.expeditions.resources)
        dialog.next_scene()
        dialog.next_scene()
        dialog.cancel_scene()
        assert colony.expeditions.resources == before
        assert not colony.expeditions.legacy_events
        assert colony.relationships.get(0, 1)['bond'] == 0
        for _ in range(3):
            dialog.next_scene()
        assert not colony.expeditions.legacy_events
        dialog.next_scene()
        assert colony.expeditions.legacy_events == [
            {'event': 'granary', 'route': 'community'}]
        assert colony.relationships.get(0, 1)['bond'] == 4
        assert colony.relationships.get(0, 1)['trust'] == 2
        assert not dialog.advance.isEnabled()
    finally:
        dialog.close()


def test_cancel_during_final_act_does_not_grant_resources(tmp_path, app):
    dialog, colony = make_dialog(tmp_path)
    try:
        previous = colony.expeditions.resources.copy()
        for _ in range(3):
            dialog.next_scene()
        dialog.cancel_scene()
        assert not colony.expeditions.legacy_events
        assert colony.expeditions.resources == previous
    finally:
        dialog.close()
