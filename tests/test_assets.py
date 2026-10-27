import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_original_six_vector_sprites_are_valid_and_transparent():
    from core.character_art import CHARACTERS, pose_svg
    from core.character_raster import raster_mascot
    art = ROOT / 'assets/monkey'
    assert len(CHARACTERS) == 6
    for personality in CHARACTERS:
        svg = pose_svg(art,personality,'idle',0,4)
        assert svg.startswith(b'<?xml')
        assert b'<script' not in svg
        with_raster = raster_mascot(art,personality,'idle',0,4)
        assert with_raster.size == (256,256)
        assert with_raster.getpixel((0,0))[3] == 0
        assert with_raster.getbbox() is not None


def test_manifest_uses_v020_generated_frames_with_legacy_timings():
    from core.character_art import CHARACTERS, pose_svg
    manifest = json.loads((ROOT / 'assets/monkey/manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema_version'] == 2
    assert manifest['canvas_px'] == [256, 256]
    for action in ('idle','blink','walk','turn','sleep','wake','fall','get_up',
                   'eat_banana','slip','angry','dragged','run'):
        state = manifest['states'][action]
        assert state['implemented']
        assert 2 <= len(state['frames']) <= 12
        assert state['fps'] > 0
        assert state['anchor_normalized'] == [0.5, 0.96]
        for persona in CHARACTERS:
            assert pose_svg(ROOT/'assets/monkey',persona,action,0,len(state['frames']))


def test_privacy_preserving_defaults():
    defaults = json.loads((ROOT / 'config/defaults.json').read_text(encoding='utf-8'))
    assert defaults['global_input_tracking'] is False
    assert defaults['start_with_windows'] is False
    assert defaults['background_network_access'] is False


def test_v07_landing_page_describes_physics_features_and_has_unique_ids():
    from html.parser import HTMLParser

    site = ROOT / 'site' / 'index.html'
    source = site.read_text(encoding='utf-8')

    class IdCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key == 'id':
                    self.ids.append(value)

    parser = IdCollector()
    parser.feed(source)
    assert len(parser.ids) == len(set(parser.ids)), 'HTML id attributes must be unique'
    assert 'v0.20 全新六猴造型候选版' in source
    assert 'id="encounterDemo"' in source
    assert '猴子关系会变化' in source
    assert '每日猴山任务' in source
    assert '可拖动的猴山家具' in source
    assert '故事卡 PNG' in source
    assert '真的会撞在一起' in source
    assert '跟随教授' in source
    assert '公共香蕉竞速' in source
    assert 'id="raceBanana"' in source
    assert 'id="raceDemo"' in source
    assert '网页按钮只是离线演示' in source
