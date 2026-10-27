"""No-browser static checks for the v0.15 offline interactive preview."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ElementScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.remote = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d:
            assert d['id'] not in self.ids, f'duplicate ID {d["id"]}'
            self.ids.add(d['id'])
        url = d.get('src') or d.get('href') or ''
        if url.startswith(('http:', 'https:')):
            self.remote.append(url)


def test_expedition_demo_in_home_navigation():
    home = (ROOT/'site/index.html').read_text(encoding='utf-8')
    assert 'href="expeditions.html"' in home
    gov = (ROOT/'site/governance.html').read_text(encoding='utf-8')
    assert 'href="./expeditions.html"' in gov


def test_purely_local_site_no_network_or_persistence():
    text = (ROOT/'site/expeditions.html').read_text(encoding='utf-8')
    reader = ElementScan()
    reader.feed(text)
    assert {'mission','crew','law','preview','launch','reset','phase',
            'lines','next','abort','bananas','science','reputation',
            'blueprints','paper','clear'}.issubset(reader.ids)
    assert not reader.remote
    assert text.count('<script>') == 1 and text.count('</script>') == 1
    for banned in ('localStorage','sessionStorage','fetch(', 'XMLHttpRequest',
                   'navigator.mediaDevices','document.cookie'):
        assert banned not in text
    assert 'aria-live="polite"' in text
    assert 'prefers-reduced-motion' in text


def test_release_notes_explicitly_say_no_actions_or_windows_validation():
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    doc = (ROOT/'docs/release_notes_v015.md').read_text(encoding='utf-8')
    assert 'GitHub Actions' in readme
    assert '[skip ci]' in doc
    assert '没有运行或触发 GitHub Actions' in doc
    assert 'Windows 真机' in doc
