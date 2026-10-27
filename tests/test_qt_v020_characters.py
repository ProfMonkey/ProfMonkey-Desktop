"""v0.20 six actual Qt desktop monkeys and source artwork, offscreen only."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from core.config import Settings
from core.profiles import clean_profiles
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.character_gallery import CharacterGallery
from ui.character_render import render_mascot

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'assets/monkey/manifest.json'
IMAGE=ROOT/'assets/characters_v020/scholar.svg'


@pytest.fixture
def app():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    return QApplication.instance() or QApplication([])


def test_six_qt_character_frames_have_distinct_pixels_and_full_bodies(app):
    seen=[]
    for persona in ('scholar','trickster','sleepy','inventor','captain','shy'):
        img=render_mascot(MANIFEST.parent,persona)
        assert img.size().width()==256 and img.size().height()==256
        assert img.toImage().pixelColor(0,0).alpha()==0
        assert not img.isNull()
        seen.append(img.toImage().bits().tobytes())
    assert len(set(seen))==6


def test_all_six_overlay_sprites_follow_personality_change_and_actions(app):
    settings=Settings(monkey_count=6,monkey_profiles=clean_profiles([]))
    primary=MonkeyOverlay(IMAGE,MANIFEST,settings=settings)
    colony=MonkeyColony(primary,IMAGE,MANIFEST)
    try:
        colony.set_count(6)
        before=[]
        for pet in colony.monkeys:
            assert pet._sprite is not None and not pet._sprite.isNull()
            assert pet._missing_frames==set()
            assert pet._sprite.size().width()==pet.settings.size
            pet.player.request('run',force=True)
            pet._set_current_sprite(force=True)
            assert not pet._sprite.isNull()
            before.append(pet._fallback_original.toImage().bits().tobytes())
        assert len(set(before))==6
        third=colony.monkeys[2]
        old=third._fallback_original.toImage().bits().tobytes()
        third.configure_profile({'name':'新发明猴','personality':'inventor'})
        assert third.personality=='inventor'
        assert third._fallback_original.toImage().bits().tobytes()!=old
        assert third._sprite_cache
        assert third._missing_frames==set()
    finally:
        colony.quit_all()


def test_character_gallery_does_not_change_game_settings(app):
    settings=Settings(monkey_count=1)
    pet=MonkeyOverlay(IMAGE,MANIFEST,settings=settings)
    colony=MonkeyColony(pet,IMAGE,MANIFEST)
    try:
        original=pet.settings.monkey_count
        dialog=CharacterGallery(colony)
        try:
            assert len(dialog.frames)==6
            assert dialog.timer.isActive()
            dialog.action.setCurrentText('walk')
            dialog.advance()
            assert all(not label.pixmap().isNull() for label,persona in dialog.frames)
        finally:
            dialog.accept()
        assert not dialog.timer.isActive()
        assert pet.settings.monkey_count==original
    finally:
        colony.quit_all()
