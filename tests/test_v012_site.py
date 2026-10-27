"""Static offline landing page checks; no network / browser required."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.resources = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get('id'):
            assert data['id'] not in self.ids, f'duplicate id: {data["id"]}'
            self.ids.add(data['id'])
        if tag == 'a':
            self.links.append(data.get('href', ''))
        if tag in ('img', 'script', 'link'):
            self.resources.append(data.get('src', data.get('href', '')))


def test_casebook_and_chemistry_are_linked_from_home():
    home = (SITE / 'index.html').read_text(encoding='utf-8')
    assert 'href="chronicle.html"' in home
    assert 'href="chemistry.html"' in home
    chemistry = (SITE / 'chemistry.html').read_text(encoding='utf-8')
    assert 'href="./chronicle.html"' in chemistry


def test_chronicle_preview_has_accessible_controls_and_no_remote_assets():
    page = (SITE / 'chronicle.html').read_text(encoding='utf-8')
    parser = PageParser()
    parser.feed(page)
    assert {'series', 'relationship', 'play', 'reset', 'line1', 'line2', 'xp',
            's0', 's1', 's2', 'phase', 'status'}.issubset(parser.ids)
    assert page.count('<script>') == 1 and page.count('</script>') == 1
    assert not any(url.startswith(('http:', 'https:')) for url in parser.resources)
    assert 'localStorage' not in page and 'fetch(' not in page
    assert 'navigator.mediaDevices' not in page
    assert len([url for url in parser.links if url and not url.startswith('#')]) >= 2
