"""Static offline tests for v0.17 multi-case monkey-city webpage."""
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.remote=[]
    def handle_starttag(self, tag, attrs):
        row=dict(attrs)
        if 'id' in row:
            assert row['id'] not in self.ids
            self.ids.add(row['id'])
        link=row.get('src') or row.get('href') or ''
        if link.startswith(('https://','http://')):
            self.remote.append(link)


def test_city_story_preview_no_remote_calls_or_data_persistence():
    src=(ROOT/'site/city_life.html').read_text(encoding='utf-8')
    inspector=Inspector()
    inspector.feed(src)
    assert {'cases','first','second','choice','preview','begin','undo','stage',
            'dialogue','next','abort','bananas','science','reputation',
            'relationship','feed','clear'}.issubset(inspector.ids)
    assert not inspector.remote
    assert src.count('<script>')==1 and src.count('</script>')==1
    for forbidden in ('localStorage','sessionStorage','fetch(', 'XMLHttpRequest',
                      'navigator.mediaDevices','document.cookie'):
        assert forbidden not in src
    assert 'prefers-reduced-motion' in src
    assert 'aria-live="polite"' in src


def test_site_integration_city_has_one_click_way_in():
    home=(ROOT/'site/index.html').read_text(encoding='utf-8')
    city=(ROOT/'site/civilization.html').read_text(encoding='utf-8')
    assert 'href="city_life.html"' in home
    assert 'href="./city_life.html"' in city


def test_development_docs_explicitly_state_no_actions_and_not_windows_verified():
    docs=(ROOT/'docs/release_notes_v017.md').read_text(encoding='utf-8')
    assert '没有运行 GitHub Actions' in docs
    assert '[skip ci]' in docs
    assert 'Windows 真机' in docs
    assert 'v0.10' in docs
