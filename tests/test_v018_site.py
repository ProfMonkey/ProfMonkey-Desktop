"""Pure offline checks for the standalone v0.18 history sandbox."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'site'


def test_history_demo_offline_and_linked():
    page = (ROOT / 'evolution.html').read_text(encoding='utf-8')
    assert '<html lang="zh-CN">' in page
    assert '<script>' in page
    assert len(re.findall(r'<script>(.*?)</script>', page, flags=re.S)) == 1
    for term in ('granary', 'star_chart', 'festival_custom', 'safety_code',
                 'constitution', 'history.push', 'scene', 'resources'):
        assert term in page
    assert 'https://' not in page and 'http://' not in page
    assert 'href="evolution.html"' in (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'href="./evolution.html"' in (ROOT / 'city_life.html').read_text(encoding='utf-8')
