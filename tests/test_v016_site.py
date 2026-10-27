"""Static city-demo and no-CI assertions; no app automation or network."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Scanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.external=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if 'id' in d:
            assert d['id'] not in self.ids
            self.ids.add(d['id'])
        link=d.get('src') or d.get('href') or ''
        if link.startswith(('https://','http://')):
            self.external.append(link)


def test_city_page_is_offline_and_interactive():
    src=(ROOT/'site/civilization.html').read_text(encoding='utf-8')
    s=Scanner()
    s.feed(src)
    assert {'tier','lots','projects','expedition','bananas','science',
            'reputation','history','reset'}.issubset(s.ids)
    assert not s.external
    assert src.count('<script>')==1 and src.count('</script>')==1
    for token in ('localStorage','sessionStorage','fetch(', 'XMLHttpRequest',
                  'navigator.mediaDevices','document.cookie'):
        assert token not in src
    assert 'prefers-reduced-motion' in src
    assert 'aria-live="polite"' in src


def test_city_demo_can_be_opened_from_home_page():
    home=(ROOT/'site/index.html').read_text(encoding='utf-8')
    journey=(ROOT/'site/expeditions.html').read_text(encoding='utf-8')
    assert 'href="civilization.html"' in home
    assert 'href="./civilization.html"' in journey


def test_docs_say_unverified_and_disable_github_actions():
    report=(ROOT/'docs/release_notes_v016.md').read_text(encoding='utf-8')
    assert '没有运行 GitHub Actions' in report
    assert '[skip ci]' in report
    assert 'Windows 真机' in report
    assert 'v0.10' in report
