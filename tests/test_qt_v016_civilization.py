"""Optional Windows/offscreen acceptance for the v0.16 native monkey city.

Run manually on a machine with recovered v0.9 art; never uses GitHub Actions.
"""
import os
from pathlib import Path
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from core.config import Settings
from core.expeditions import ExpeditionJournal
from core.relationships import RelationshipStore
from core.governance import MonkeyLaws
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.civilization_dialog import CivilizationDialog


@pytest.fixture(scope='module')
def app():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    instance=QApplication.instance() or QApplication([])
    yield instance
    instance.processEvents()


def make_colony(tmp_path):
    root=Path(__file__).resolve().parents[1]
    picture=root/'assets/monkey/idle.png'
    manifest=root/'assets/monkey/manifest.json'
    if not picture.is_file():
        pytest.skip('restore verified v0.9 art to run native Qt tests')
    settings=Settings(monkey_count=3, monkey_profiles=[
        {'name':'皮猴','personality':'trickster'},
        {'name':'发明猴','personality':'inventor'},
        {'name':'学究猴','personality':'scholar'}]).validated()
    primary=MonkeyOverlay(picture,manifest,settings=settings)
    colony=MonkeyColony(primary,picture,manifest)
    colony.expeditions=ExpeditionJournal(tmp_path/'expeditions.json')
    colony.relationships=RelationshipStore(tmp_path/'relationships.json')
    colony.laws=MonkeyLaws(tmp_path/'monkey_laws.json')
    primary.show()
    colony.set_count(3)
    return colony


def test_user_builds_and_displays_one_city_building(tmp_path,app,monkeypatch):
    colony=make_colony(tmp_path)
    try:
        from PySide6.QtWidgets import QMessageBox
        colony.expeditions.resources.update(bananas=15,science=20,reputation=20)
        dialog=CivilizationDialog(colony)
        assert dialog.build_button.isEnabled()
        assert not dialog.show_button.isEnabled()
        monkeypatch.setattr(QMessageBox,'question',lambda *_args:
                            QMessageBox.StandardButton.Yes)
        dialog.build()
        assert colony.expeditions.buildings==frozenset({'banana_vault'})
        assert colony.expeditions.resources['bananas']==3
        assert colony.expeditions.path.is_file()
        assert dialog.show_button.isEnabled()
        dialog.display()
        assert any(prop.kind=='banana_vault' for prop in colony.furniture)
        assert colony.display_city_building('banana_vault')
        assert sum(p.kind=='banana_vault' for p in colony.furniture)==1
        assert not colony.display_city_building('monkey_academy')
        assert not colony.place_furniture('galaxy_scope')
        dialog.close()
    finally:
        colony.quit_all()


def test_city_modifies_real_expedition_and_clear_removes_props(tmp_path,app):
    colony=make_colony(tmp_path)
    try:
        colony.expeditions.resources.update(bananas=19,science=15,reputation=15)
        assert colony.expeditions.construct('banana_vault')
        assert colony.display_city_building('banana_vault')
        assert colony.start_expedition('banana_scout',(0,1))
        assert colony.expedition.plan.city_buildings==frozenset({'banana_vault'})
        assert colony.expedition.plan.outcome=='success'
        while not colony.expedition.finished:
            colony.expedition.advance(.4)
        colony._complete_expedition()
        colony._complete_expedition()
        colony.cancel_expedition()
        assert colony.expeditions.resources['bananas']==13  # 19-12+6
        assert colony.expeditions.missions[0]==1
        colony.clear_expeditions()
        assert not colony.expeditions.buildings
        assert not colony.expeditions.path.exists()
        assert not any(prop.kind=='banana_vault' for prop in colony.furniture)
    finally:
        colony.quit_all()


def test_building_click_keeps_it_entirely_inside_game(tmp_path,app):
    colony=make_colony(tmp_path)
    try:
        colony.expeditions.resources.update(bananas=12)
        assert colony.expeditions.construct('banana_vault')
        assert colony.display_city_building('banana_vault')
        building=next(x for x in colony.furniture if x.kind=='banana_vault')
        # Clicking starts only a monkey animation/speech, not a system task.
        colony._interact_furniture(building)
        assert colony.expeditions.resources['bananas']==0
        assert not colony._race_active
    finally:
        colony.quit_all()
