"""v0.13 completely offline and selectable society landing page regression checks."""
from html.parser import HTMLParser
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.external=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'duplicate html id'
            self.ids.add(attrs['id'])
        value=attrs.get('src') or attrs.get('href')
        if value and (value.startswith('http://') or value.startswith('https://')):
            self.external.append(value)


def test_home_links_to_offline_council_preview():
    text=(ROOT/'site/index.html').read_text(encoding='utf-8')
    assert 'href="society.html"' in text


def test_council_page_controls_and_no_remote_dependencies():
    text=(ROOT/'site/society.html').read_text(encoding='utf-8')
    page=Page()
    page.feed(text)
    assert {
        'cast','issue','start','next','scene','stage','yes','no','abstain',
        'outcome','network','groups','addFriend','addRival','reset'
    }.issubset(page.ids)
    assert page.external == []
    assert text.count('<script>') == 1
    assert text.count('</script>') == 1
    assert 'localStorage' not in text
    assert 'sessionStorage' not in text
    assert 'fetch(' not in text
    assert 'XMLHttpRequest' not in text
    assert 'navigator.mediaDevices' not in text


def test_documentation_explicitly_marks_candidate_not_real_windows_acceptance():
    notes=(ROOT/'docs/release_notes_v013.md').read_text(encoding='utf-8')
    assert 'Windows 真机' in notes and '由用户手动选择' in notes
