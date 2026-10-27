"""v0.14 offscreen Qt acceptance: votes enact actual monkey-only effects."""
import os
from pathlib import Path

import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from core.governance import MonkeyLaws
from core.relationships import RelationshipStore
from ui.colony import MonkeyColony
from ui.overlay import MonkeyOverlay
from ui.law_dialog import MonkeyLawDialog


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    created=QApplication.instance() or QApplication([])
    yield created
    created.processEvents()


def colony_with_inventor(tmp_path):
    root=Path(__file__).resolve().parents[1]
    art,manifest=root/'assets/monkey/idle.png',root/'assets/monkey/manifest.json'
    if not art.is_file():
        pytest.skip('requires original v0.9 binary art')
    settings=Settings(monkey_count=3, monkey_profiles=[
        {'name':'皮猴','personality':'trickster'},
        {'name':'发明猴','personality':'inventor'},
        {'name':'学究猴','personality':'scholar'}]).validated()
    primary=MonkeyOverlay(art,manifest,settings=settings)
    colony=MonkeyColony(primary,art,manifest)
    colony.relationships=RelationshipStore(tmp_path/'relationships.json')
    colony.laws=MonkeyLaws(tmp_path/'monkey_laws.json')
    primary.show()
    colony.set_count(3)
    return colony


def finish_council(colony):
    while not colony.council.finished:
        colony.council.advance(.4)
    colony._complete_council()
    colony.cancel_council()


def test_council_rocket_law_requires_complete_vote_and_can_be_repealed(tmp_path,app):
    colony=colony_with_inventor(tmp_path)
    try:
        assert not colony.start_rocket_trial()
        assert colony.start_council('rocket_license',(0,1,2))
        assert colony.council.plan.result=='adopted'
        colony._complete_council()
        assert not colony.laws.file.exists()
        assert not colony.start_rocket_trial()
        colony.toggle_pause(True)
        assert not colony.council.active and not colony.laws.file.exists()
        colony.toggle_pause(False)
        assert colony.start_council('rocket_license',(0,1,2))
        finish_council(colony)
        assert colony.laws.active('rocket_license')
        assert len(colony.laws.history)==1
        assert colony.start_rocket_trial()
        assert colony.social.name=='rocket_trial'
        assert all(p._social_active for p in colony.monkeys)
        assert not colony.start_council('banana_rules',(0,1,2))
        assert not colony.drop_shared_banana()
        colony.hide_all()
        assert not colony.social.active or all(not p.isVisible() for p in colony.monkeys)
        colony.cancel_social()
        colony.show_all()
        colony.clear_monkey_laws()
        assert not colony.start_rocket_trial()
        assert not colony.laws.file.exists()
    finally:
        colony.quit_all()


def test_legislative_banana_sharing_uses_real_relations(tmp_path,app):
    colony=colony_with_inventor(tmp_path)
    try:
        assert colony.start_council('banana_rules',(0,1,2))
        assert colony.council.plan.result=='rejected'  # trickster and inventor oppose
        finish_council(colony)
        assert not colony.laws.active('banana_rules')
        assert colony.start_council('banana_rules',(2,0,1))
        # Same monkeys have same majority; cannot force adoption via relabeling.
        assert colony.council.plan.result=='rejected'
        colony.cancel_council()
        colony.laws.enact('banana_rules','adopted')  # simulate prior completed other council
        assert colony.laws.active('banana_rules')
        assert colony.drop_shared_banana()
        winner=colony.monkeys[0]
        old=colony.relationships.get(0,1)
        colony._claim_shared_banana(winner)
        newer=colony.relationships.get(0,1)
        assert newer['bond'] > old['bond']
        assert newer['rivalry'] <= old['rivalry']
        assert newer['interactions'] == old['interactions'] + 1
        assert not colony._race_active
    finally:
        colony.quit_all()


def test_quiet_policy_does_not_block_manual_encounter_and_lawbook(tmp_path,app):
    colony=colony_with_inventor(tmp_path)
    try:
        colony.laws.enact('quiet_hours','adopted')
        dialog=MonkeyLawDialog(colony,colony.laws)
        assert '正在生效' in dialog.summary.toPlainText()
        assert not dialog.launch_button.isEnabled()
        dialog.close()
        assert colony.demo_pair(0,1)
        assert colony.duo.active
        colony.toggle_pause(True)
        assert not colony.duo.active
        assert colony.laws.active('quiet_hours')
        colony.toggle_pause(False)
    finally:
        colony.quit_all()
