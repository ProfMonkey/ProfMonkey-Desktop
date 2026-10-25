"""Qt smoke checks; run on Windows/with PySide6 or QT_QPA_PLATFORM=offscreen."""
import os
from pathlib import Path
import pytest

qt=pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from core.config import Settings
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.colony_panel import ColonyPanel


def test_real_pets_have_distinct_profiles_and_social_stages():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    app=QApplication.instance() or QApplication([])
    root=Path(__file__).resolve().parents[1]
    image=root/'assets/monkey/idle.png'
    manifest=root/'assets/monkey/manifest.json'
    settings=Settings(monkey_count=3,monkey_profiles=[
        {'name':'甲猴','personality':'scholar'},
        {'name':'乙猴','personality':'trickster'},
        {'name':'丙猴','personality':'sleepy'},
    ]).validated()
    primary=MonkeyOverlay(image,manifest,settings=settings)
    colony=MonkeyColony(primary,image,manifest)
    try:
        primary.show()
        colony.set_count(3)
        assert [m.display_name for m in colony.monkeys]==['甲猴','乙猴','丙猴']
        assert [m.brain.personality for m in colony.monkeys]==['scholar','trickster','sleepy']
        assert colony.start_social('meeting')
        assert all(m._social_active for m in colony.monkeys)
        assert not colony.start_social('banana_duel')
        colony.cancel_social()
        assert not any(m._social_active for m in colony.monkeys)
        panel=ColonyPanel(settings)
        panel.count.setValue(2)
        panel.names[0].setText('超级猴')
        candidate=panel.updated(settings)
        assert candidate.monkey_profiles[0]['name']=='超级猴'
        assert candidate.monkey_count==2
        panel.close()
    finally:
        colony.quit_all()
