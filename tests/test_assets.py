import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_original_sprite_is_transparent_256px_placeholder():
    image = Image.open(ROOT / 'assets/monkey/idle.png').convert('RGBA')
    assert image.size == (256, 256)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((125, 105))[3] > 24
    assert 0 < image.getbbox()[0] < 128


def test_manifest_matches_p02_png_sequences():
    manifest = json.loads((ROOT / 'assets/monkey/manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema_version'] == 2
    assert manifest['canvas_px'] == [256, 256]
    for action in ('idle','blink','walk','turn','sleep','wake','fall','get_up'):
        state = manifest['states'][action]
        assert state['implemented']
        assert 2 <= len(state['frames']) <= 12
        assert state['fps'] > 0
        for frame in state['frames']:
            p = ROOT / 'assets/monkey' / frame
            with Image.open(p) as img:
                assert img.mode == 'RGBA' and img.size == (256,256), frame
                assert img.getpixel((0,0))[3] == 0, frame
                assert img.getbbox(), frame
    assert manifest['states']['eat_banana']['implemented']


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
    assert 'v0.9 猴山偶遇候选版' in source
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
