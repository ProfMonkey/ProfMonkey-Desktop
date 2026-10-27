"""Optional v0.17 Qt smoke: two independently animated characters, exactly-once city story.

Only run locally with original verified v0.9 art; never through GitHub Actions.
"""
import os
from pathlib import Path
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from core.expeditions import ExpeditionJournal
from core.relationships import RelationshipStore
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.city_life_dialog import CityLifeDialog


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    instance=QApplication.instance() or QApplication([])
    yield instance
    instance.processEvents()


def make_colony(tmp_path):
    root=Path(__file__).resolve().parents[1]
    art=root/'assets/monkey/idle.png'
    manifest=root/'assets/monkey/manifest.json'
    if not art.is_file():
        pytest.skip('v0.9 recovered original artwork required')
    settings=Settings(monkey_count=3,monkey_profiles=[
        {'name':'学究猴','personality':'scholar'},
        {'name':'皮猴','personality':'trickster'},
        {'name':'发明猴','personality':'inventor'}]).validated()
    primary=MonkeyOverlay(art,manifest,settings=settings)
    colony=MonkeyColony(primary,art,manifest)
    colony.expeditions=ExpeditionJournal(tmp_path/'expeditions.json')
    colony.relationships=RelationshipStore(tmp_path/'relationships.json')
    colony.expeditions.resources.update(bananas=55,science=60,reputation=60)
    primary.show()
    colony.set_count(3)
    return colony


def advance_end(colony):
    while not colony.city_life.finished:
        colony.city_life.advance(.4)
    colony._complete_city_life()


def test_staged_city_story_requires_complete_three_acts(tmp_path,app):
    colony=make_colony(tmp_path)
    try:
        assert not colony.start_city_life('banana_vault',0,1,'careful')
        assert colony.expeditions.construct('banana_vault')
        initial=dict(colony.expeditions.resources)
        assert colony.start_city_life('banana_vault',0,1,'careful')
        assert all(colony.monkeys[i]._social_active for i in (0,1))
        assert not colony.monkeys[2]._social_active
        assert not colony.start_expedition('banana_scout',(0,1))
        assert not colony.start_social('meeting')
        assert not colony.drop_shared_banana()
        colony._complete_city_life()  # pre-finish must not pay anything
        assert colony.expeditions.city_cases['banana_vault']['chapter']==0
        assert colony.expeditions.resources==initial
        colony.toggle_pause(True)
        assert not colony.city_life.active
        assert colony.expeditions.city_cases['banana_vault']['chapter']==0
        colony.toggle_pause(False)
        assert colony.start_city_life('banana_vault',0,1,'careful')
        advance_end(colony)
        colony._complete_city_life()  # second call must never pay again
        assert colony.expeditions.resources['bananas']==initial['bananas']-1
        assert colony.expeditions.city_cases['banana_vault']['chapter']==1
        assert colony.relationships.get(0,1)['bond']==2
        colony.cancel_city_life()
        assert not any(p._social_active for p in colony.monkeys)
    finally:
        colony.quit_all()


def test_city_book_only_enables_constructed_cases_and_prevents_replay(tmp_path,app):
    colony=make_colony(tmp_path)
    try:
        dialog=CityLifeDialog(colony)
        assert not dialog.start_button.isEnabled()
        dialog.close()
        assert colony.expeditions.construct('banana_vault')
        dialog=CityLifeDialog(colony,'banana_vault')
        assert dialog.case.currentData()=='banana_vault'
        assert dialog.start_button.isEnabled()
        dialog.second.setCurrentIndex(0)
        assert not dialog.start_button.isEnabled()
        dialog.second.setCurrentIndex(1)
        assert dialog.start_button.isEnabled()
        dialog.close()
        for choice in ('careful','careful','careful'):
            assert colony.start_city_life('banana_vault',0,1,choice)
            advance_end(colony)
            colony.cancel_city_life()
        assert not colony.start_city_life('banana_vault',0,1,'careful')
        assert colony.expeditions.city_cases['banana_vault']['ending']=='reconciled'
        dialog=CityLifeDialog(colony,'banana_vault')
        assert not dialog.start_button.isEnabled()
        dialog.close()
    finally:
        colony.quit_all()


def test_hide_and_clear_remove_active_city_event_without_extra_rewards(tmp_path,app):
    colony=make_colony(tmp_path)
    try:
        colony.expeditions.construct('banana_vault')
        assert colony.start_city_life('banana_vault',0,1,'bold')
        colony.hide_all()
        assert not colony.city_life.active
        assert colony.expeditions.city_cases['banana_vault']['chapter']==0
        colony.show_all()
        assert colony.start_city_life('banana_vault',0,1,'careful')
        colony.clear_expeditions()
        assert not colony.city_life.active
        assert not colony.expeditions.buildings
        assert not colony.expeditions.path.exists()
    finally:
        colony.quit_all()
