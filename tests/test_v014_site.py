"""Static guarantees for v0.14 offline preview and discoverability."""
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.external=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'duplicate element id'
            self.ids.add(attrs['id'])
        val=attrs.get('src') or attrs.get('href') or ''
        if val.startswith(('https://','http://')):
            self.external.append(val)


def test_lawbook_demo_offline_and_complete():
    source=(ROOT/'site/governance.html').read_text(encoding='utf-8')
    parser=Parse();parser.feed(source)
    assert {'ruleCards','issue','yes','no','tie','voteResult','banana','auto',
            'rocket','scene','history','clear'}.issubset(parser.ids)
    assert not parser.external
    assert source.count('<script>')==1 and source.count('</script>')==1
    assert 'localStorage' not in source
    assert 'sessionStorage' not in source
    assert 'fetch(' not in source
    assert 'navigator.mediaDevices' not in source


def test_home_links_new_society_and_lawbook_previews():
    home=(ROOT/'site/index.html').read_text(encoding='utf-8')
    assert 'href="society.html"' in home
    assert 'href="governance.html"' in home


def test_lawbook_candidate_doc_does_not_claim_real_windows_acceptance():
    text=(ROOT/'docs/release_notes_v014.md').read_text(encoding='utf-8')
    assert 'Windows 真机' in text and '源码候选' in text
