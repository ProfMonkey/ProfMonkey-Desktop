"""Optional Windows offscreen smoke for v0.15 expedition actual GUI integration.

Not run automatically; use locally with explicit QT_QPA_PLATFORM=offscreen.
"""
import os
from pathlib import Path
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from core.relationships import RelationshipStore
from core.governance import MonkeyLaws
from core.expeditions import ExpeditionJournal
from ui.colony import MonkeyColony
from ui.overlay import MonkeyOverlay
from ui.expedition_dialog import ExpeditionDialog


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    obj=QApplication.instance() or QApplication([])
    yield obj
    obj.processEvents()


def create_colony(tmp_path):
    root=Path(__file__).resolve().parents[1]
    art,manifest=root/'assets/monkey/idle.png',root/'assets/monkey/manifest.json'
    if not art.is_file():
        pytest.skip('legacy v0.9 art missing from checkout')
    prefs=Settings(monkey_count=3,monkey_profiles=[
        {'name':'皮猴','personality':'trickster'},
        {'name':'发明猴','personality':'inventor'},
        {'name':'学究猴','personality':'scholar'}]).validated()
    primary=MonkeyOverlay(art,manifest,settings=prefs)
    colony=MonkeyColony(primary,art,manifest)
    colony.relationships=RelationshipStore(tmp_path/'relationships.json')
    colony.laws=MonkeyLaws(tmp_path/'monkey_laws.json')
    colony.expeditions=ExpeditionJournal(tmp_path/'expeditions.json')
    primary.show()
    colony.set_count(3)
    return colony


def test_manual_mission_cancel_prevents_rewards_and_replay_is_exactly_once(tmp_path,app):
    colony=create_colony(tmp_path)
    try:
        assert colony.start_expedition('banana_scout',(0,1))
        assert all(colony.monkeys[i]._social_active for i in (0,1))
        assert not colony.start_council('quiet_hours',(0,1,2))
        assert not colony.start_social('meeting')
        assert not colony.drop_shared_banana()
        colony._complete_expedition()  # not finished
        assert not colony.expeditions.path.exists()
        colony.toggle_pause(True)
        assert not colony.expedition.active
        assert not colony.expeditions.path.exists()
        assert not any(p._social_active for p in colony.monkeys)
        colony.toggle_pause(False)
        assert colony.start_expedition('banana_scout',(0,1))
        while not colony.expedition.finished:
            colony.expedition.advance(.4)
        assert colony.expedition.plan.outcome=='mixed'
        colony._complete_expedition()
        colony._complete_expedition()
        assert colony.expeditions.resources['bananas']==2
        assert colony.expeditions.missions[0]==1
        assert colony.relationships.get(0,1)['interactions']==1
        colony.cancel_expedition()
        assert not any(p._social_active for p in colony.monkeys)
    finally:
        colony.quit_all()


def test_law_snapshot_affects_explicit_expedition_reward(tmp_path,app):
    colony=create_colony(tmp_path)
    try:
        colony.laws.enact('banana_rules','adopted')
        assert colony.start_expedition('banana_scout',(0,1))
        plan=colony.expedition.plan
        assert plan.law_boost and plan.outcome=='success'
        assert plan.rewards==(6,1,1)
        colony.laws.enact('banana_rules','rejected')  # current law changed mid-scene
        while not colony.expedition.finished:
            colony.expedition.advance(.4)
        colony._complete_expedition()
        colony.cancel_expedition()
        assert colony.expeditions.resources['bananas']==6  # started snapshot wins
        assert not colony.laws.active('banana_rules')
    finally:
        colony.quit_all()


def test_mission_ui_checks_roster_and_hide_interrupts(tmp_path,app):
    colony=create_colony(tmp_path)
    try:
        dialog=ExpeditionDialog(colony)
        assert dialog.selected()==(0,1)
        assert dialog.launch.isEnabled()
        dialog.checks[1].setChecked(False)
        assert not dialog.launch.isEnabled()
        dialog.checks[1].setChecked(True)
        assert dialog.launch.isEnabled()
        dialog.close()
        assert colony.start_expedition('meteor_lab',(1,2))
        colony.hide_all()
        assert not colony.expedition.active
        assert not colony.expeditions.path.exists()
        colony.show_all()
        colony.set_count(1)
        assert not colony.start_expedition('meteor_lab',(1,2))
    finally:
        colony.quit_all()
