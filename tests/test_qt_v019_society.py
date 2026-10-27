"""Optional v0.19 Qt observer smoke. Run manually with PySide6 offscreen."""
import os
from types import SimpleNamespace
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication

from core.config import Settings
from core.civic_society import city_society
from core.expeditions import ExpeditionJournal
from ui.society_dialog import SocietyDialog


@pytest.fixture
def app():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    yield QApplication.instance() or QApplication([])


class FakeColony:
    def __init__(self, tmp_path):
        settings = Settings(mode='MONKEY',monkey_count=2).validated()
        self.primary = SimpleNamespace(settings=settings)
        self.expeditions = ExpeditionJournal(tmp_path/'expeditions.json')
        self.laws = None
        self.relationships = None
        self.monkeys = [SimpleNamespace(display_name='学究猴',personality='scholar'),
                        SimpleNamespace(display_name='皮猴',personality='trickster')]
        self.count = 2
        self.demo_calls = 0

    def society_snapshot(self):
        return city_society(self.expeditions,profiles=self.primary.settings.monkey_profiles,
                            count=self.count)

    def set_civic_autonomy(self, enabled):
        self.primary.settings.civic_autonomy=bool(enabled)

    def set_ambient_encounters(self, enabled):
        self.primary.settings.ambient_encounters=bool(enabled)

    def demo_pair(self,a,b):
        self.demo_calls+=1
        return a!=b


def test_civic_observer_requires_opt_in_and_never_writes_journal(tmp_path,app):
    colony=FakeColony(tmp_path)
    saves=[]
    dialog=SocietyDialog(colony,lambda:saves.append('settings'))
    try:
        assert not dialog.enabled.isChecked()
        assert not dialog.observe.isEnabled()
        assert not colony.expeditions.path.exists()
        dialog.enabled.setChecked(True)
        assert colony.primary.settings.civic_autonomy
        assert dialog.observe.isEnabled()
        dialog._observe()
        assert colony.demo_calls==1
        assert len(saves)==1
        dialog.enabled.setChecked(False)
        assert not dialog.observe.isEnabled()
        assert not colony.expeditions.path.exists()
    finally:
        dialog.close()


def test_ambient_switch_independent_and_count_gate(tmp_path,app):
    colony=FakeColony(tmp_path)
    dialog=SocietyDialog(colony)
    try:
        dialog.ambient.setChecked(True)
        assert colony.primary.settings.ambient_encounters
        assert not colony.primary.settings.civic_autonomy
        assert not dialog.observe.isEnabled()
        dialog.enabled.setChecked(True)
        dialog.second.setCurrentIndex(0)
        assert not dialog.observe.isEnabled()
    finally:
        dialog.close()
