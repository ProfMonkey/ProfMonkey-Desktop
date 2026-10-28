"""Manual Qt smoke for hidden story dialog; no desktop capture."""
import os
from pathlib import Path
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QMenu
from core.config import Settings
from core.secrets import SecretJournal
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.secret_dialog import SecretDialog

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/characters_v020/scholar.svg'
MANIFEST=ROOT/'assets/monkey/manifest.json'


@pytest.fixture
def app():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    return QApplication.instance() or QApplication([])


def test_ui_six_story_cases_and_gestures(app,tmp_path):
    settings=Settings(mode='MONKEY',monkey_count=2)
    primary=MonkeyOverlay(ART,MANIFEST,settings=settings)
    colony=MonkeyColony(primary,ART,MANIFEST)
    try:
        journal=SecretJournal(tmp_path/'eggs.json')
        colony.bind_secrets(journal)
        menu=QMenu()
        colony.bind_menu(menu,lambda pet:None)
        colony.set_count(2)
        assert any('隐藏事件簿' in a.text() for a in menu.actions())
        for _ in range(3):
            assert primary.feed_banana()
        assert journal.gestures['feeds']==3
        dialog=SecretDialog(colony)
        try:
            assert dialog.case.count()==6
            assert dialog.start.isEnabled()
            assert not journal.cleared('banana_receipt')
        finally:
            dialog.close()
    finally:
        colony.quit_all()
