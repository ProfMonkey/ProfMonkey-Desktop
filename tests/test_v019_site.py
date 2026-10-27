"""v0.19 web demo offline smoke; pure Python, no Qt or network needed."""
from pathlib import Path
import re

SITE = Path(__file__).resolve().parents[1]/'site'


def test_civic_sandbox_is_standalone_and_no_remote_resources():
    html = (SITE/'civic_society.html').read_text(encoding='utf-8')
    assert '<html lang="zh-CN">' in html
    assert html.count('<script>') == html.count('</script>') == 1
    assert not re.search(r'https?://|<iframe|<script\s+src',html,re.I)
    for token in ('banana_vault','galaxy_scope','public_square',
                  'monkey_academy','granary','star_chart','festival_custom',
                  'safety_code','constitution','trust','rivalry','bond',
                  'cooperation','innovation','tension','meet','routine'):
        assert token in html


def test_v019_links_are_visible_from_index_and_v018_history():
    index = (SITE/'index.html').read_text(encoding='utf-8')
    history = (SITE/'evolution.html').read_text(encoding='utf-8')
    assert 'href="civic_society.html"' in index
    assert 'href="civic_society.html"' in history
    assert (SITE/'society.html').is_file(), 'older v0.13 society demo stays intact'
