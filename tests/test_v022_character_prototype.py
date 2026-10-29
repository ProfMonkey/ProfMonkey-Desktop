"""v0.22 checks for the shared professor-monkey prototype."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path

from core.character_art import CHARACTERS, mascot_path, pose_svg
from core.profiles import PERSONALITIES, clean_profiles

ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = ROOT / "assets" / "monkey"
NS = "{http://www.w3.org/2000/svg}"


def test_six_role_names_and_default_order_match_the_approved_sheet():
    assert list(CHARACTERS) == ["scholar", "captain", "inventor", "sleepy", "trickster", "shy"]
    assert [PERSONALITIES[k] for k in CHARACTERS] == ["教授猴", "探险猴", "编程猴", "摸鱼猴", "干饭猴", "酷帅猴"]
    assert [p["personality"] for p in clean_profiles([])] == list(CHARACTERS)


def test_six_svg_assets_share_the_same_body_face_tail_and_animation_contract():
    drawings = []
    for key in CHARACTERS:
        path = mascot_path(ART_ROOT, key)
        data = path.read_bytes()
        root = ET.fromstring(data)
        assert root.tag == NS + "svg"
        assert root.attrib["viewBox"] == "0 0 256 256"
        text = data.decode("utf-8")
        for marker in (
            'id="body"', 'id="tail-outline"', 'fill="#C97D42"', 'fill="#FFE7C4"',
            'stroke="#2A1912"', 'cx="74" cy="99"', 'cy="245"',
            'id="head" transform="translate(128 104) scale(.84)',
            'id="pose" transform="translate(0 0)"',
            'id="left-leg" transform="translate(0 0)"',
            'id="right-leg" transform="translate(0 0)"',
            'id="left-arm" transform="translate(0 0)"',
            'id="right-arm" transform="translate(0 0)"',
            'id="eyes-open" opacity="1"', 'id="eyes-closed" opacity="0"',
            'id="mouth-smile" opacity="1"', 'id="mouth-open" opacity="0"',
            'id="prop-banana" opacity="0"',
        ):
            assert marker in text
        assert "<script" not in text.lower()
        assert "<foreignobject" not in text.lower()
        assert 'href="http' not in text.lower()
        drawings.append(text)
    assert len(set(drawings)) == 6


def test_all_existing_animation_actions_still_produce_valid_svg_frames():
    for key in CHARACTERS:
        for action in ("idle", "blink", "walk", "turn", "sleep", "wake", "fall",
                       "get_up", "eat_banana", "slip", "angry", "dragged", "run"):
            frame = pose_svg(ART_ROOT, key, action, 0, 4)
            assert ET.fromstring(frame).attrib["viewBox"] == "0 0 256 256"


def test_gallery_and_windows_repair_script_are_updated():
    gallery = (ROOT / "site" / "characters.html").read_text(encoding="utf-8")
    renderer = (ROOT / "ui" / "character_render.py").read_text(encoding="utf-8")
    setup = (ROOT / "setup_windows.bat").read_text(encoding="utf-8")
    for name in ("教授猴", "探险猴", "编程猴", "摸鱼猴", "干饭猴", "酷帅猴"):
        assert name in gallery
    assert "QtSvg" in renderer
    assert "force-reinstall" in setup
    assert "monkey_spritesheet_3x2.png" not in renderer
