"""v0.20 original six character regression gates; no Qt or network needed."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from core.character_art import (
    CHARACTERS, SUPPORTED_ACTIONS, mascot_path, pose_svg
)
from core.profiles import clean_profiles

ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = ROOT/'assets'/'monkey'
NS = '{http://www.w3.org/2000/svg}'


def test_six_mascots_are_unique_valid_svg_and_have_bodies():
    content = []
    for personality in CHARACTERS:
        path = mascot_path(ART_ROOT,personality)
        assert path.is_file()
        data = path.read_bytes()
        root = ET.fromstring(data)
        assert root.tag == NS+'svg'
        assert root.attrib['viewBox'] == '0 0 256 256'
        assert root.attrib['width'] == '256'
        assert root.attrib['height'] == '256'
        assert b'<script' not in data.lower() and b'http://' not in data.lower()
        group_ids = {node.get('id') for node in root.iter() if node.get('id')}
        assert {'pose','left-leg','right-leg','left-arm','right-arm',
                'eyes-open','eyes-closed','mouth-open','mouth-smile','prop-banana'}.issubset(group_ids)
        assert b'cx="74" cy="99"' in data
        assert b'cy="245"' in data  # shared bottom contact anchor
        content.append(data)
    assert len(content) == len(set(content)) == 6


def test_six_default_personalities_have_six_corresponding_images():
    people = clean_profiles([])
    assert [p['personality'] for p in people] == list(CHARACTERS)
    assert all(mascot_path(ART_ROOT,p['personality']).exists() for p in people)


@pytest.mark.parametrize('personality', CHARACTERS)
@pytest.mark.parametrize('action,frames',[
    ('idle',4),('blink',4),('walk',8),('turn',7),('sleep',4),
    ('wake',5),('fall',6),('get_up',6),('eat_banana',6),
    ('slip',4),('angry',4),('dragged',2),('run',6)
])
def test_every_mascot_action_generates_valid_same_canvas(personality,action,frames):
    for frame in range(frames):
        svg = pose_svg(ART_ROOT,personality,action,frame,frames)
        root = ET.fromstring(svg)
        assert root.attrib['viewBox'] == '0 0 256 256'
        assert NS+'g' in {n.tag for n in root.iter()}
        assert b'id="pose"' in svg
    if action == 'blink':
        assert b'id="eyes-closed" opacity="1"' in pose_svg(ART_ROOT,personality,action,1,4)


def test_posed_monkeys_are_independently_changed():
    professor = pose_svg(ART_ROOT,'scholar','idle',0,4)
    professor_walk = pose_svg(ART_ROOT,'scholar','walk',1,8)
    trickster = pose_svg(ART_ROOT,'trickster','idle',0,4)
    assert professor != professor_walk
    assert professor != trickster
    assert b'rotate(' in professor_walk
    assert b'rotate(0 128 192)' in pose_svg(ART_ROOT,'scholar','idle',0,4)


@pytest.mark.parametrize('arg',[
    ('unknown','idle',0,1),('scholar','jump',0,1),
    ('scholar','walk',-1,8),('scholar','walk',8,8),
    ('scholar','idle',0,0),('scholar','idle',True,4)
])
def test_malformed_in_game_character_requests_are_rejected(arg):
    with pytest.raises(ValueError):
        pose_svg(ART_ROOT,*arg)


def test_site_links_point_to_six_real_svg_characters():
    site = (ROOT/'site'/'characters.html').read_text(encoding='utf-8')
    index = (ROOT/'site'/'index.html').read_text(encoding='utf-8')
    society = (ROOT/'site'/'civic_society.html').read_text(encoding='utf-8')
    assert 'href="characters.html"' in index
    assert 'src="../assets/characters_v020/scholar.svg"' in index
    for personality in CHARACTERS:
        assert f'../assets/characters_v020/{personality}.svg' in site
    assert 'assets/characters_v020/' in society
    assert 'assets/monkey.png' not in index


def test_real_raster_uses_self_contained_sources_if_cairosvg_available():
    pytest.importorskip('cairosvg')
    from core.character_raster import raster_mascot
    shots = []
    for personality in CHARACTERS:
        image = raster_mascot(ART_ROOT,personality,'idle',0,4)
        assert image.size == (256,256)
        assert image.getpixel((0,0))[3] == 0
        assert image.getbbox() is not None
        shots.append(image.tobytes())
    assert len(set(shots)) == 6


def test_new_portrait_and_story_card_individual_character_assets(tmp_path):
    pytest.importorskip('cairosvg')
    from core.portrait import render_colony_portrait
    from core.story_card import render_story_card
    profiles = clean_profiles([])
    portrait=tmp_path/'portrait.png'
    card=tmp_path/'story.png'
    assert render_colony_portrait(ART_ROOT/'idle.png',profiles,6,portrait) == (1000,660)
    assert render_story_card(ART_ROOT/'idle.png',profiles,6,'banana',card) == (1200,800)
    assert portrait.stat().st_size > 10_000
    assert card.stat().st_size > 10_000
