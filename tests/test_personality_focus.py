"""Offline personality, timer and landing page regression gates (no Qt required)."""
from pathlib import Path
from html.parser import HTMLParser
import json
import pytest
from core.focus import FocusClock, format_seconds
from core.config import Settings, ConfigStore
from core.progress import ProgressStore, BADGES, COUNTERS


def test_focus_lifecycle_pause_and_one_shot_completion():
    f = FocusClock()
    f.start(25, now=100)
    assert f.remaining(now=100) == 1500
    assert not f.check_complete(now=1499)
    assert f.pause(now=200)
    assert f.remaining(now=3000) == 1400
    assert not f.check_complete(now=9999)
    assert f.resume(now=5000)
    assert f.remaining(now=5001) == 1399
    assert f.check_complete(now=6400)
    assert not f.check_complete(now=6401)
    assert f.state == 'completed'
    f.cancel()
    assert f.state == 'idle' and not f.active


def test_focus_invalid_lengths_and_formatting():
    f = FocusClock()
    for bad in [0, 181, -1, 2.5, True, '25']:
        with pytest.raises(ValueError):
            f.start(bad)
    assert format_seconds(1500) == '25:00'
    assert format_seconds(61) == '01:01'
    assert format_seconds(-1) == '00:00'


def test_progress_is_opt_in_and_persistent(tmp_path):
    file = tmp_path / 'progress.json'
    progress = ProgressStore(file)
    assert progress.record('feeds') == []
    assert not file.exists()
    progress.enable()
    assert progress.record('feeds') == ['🍌 香蕉初体验']
    for _ in range(9):
        progress.record('feeds')
    assert 'banana_king' in progress.unlocked()
    loaded = ProgressStore(file, enabled=True)
    assert loaded.counts['feeds'] == 10
    assert loaded.record('focus_minutes', 120)
    assert loaded.record('focus_sessions')
    assert len(loaded.unlocked()) >= 4
    loaded.disable()
    loaded.record('taps')
    assert ProgressStore(file, enabled=True).counts['taps'] == 0
    loaded.clear()
    assert not file.exists()


def test_progress_whitelist_and_bad_data(tmp_path):
    file = tmp_path / 'progress.json'
    file.write_text(json.dumps({'feeds': -5, 'taps': True, 'stories': 7,
                                'private': 'never load', 'focus_minutes': 15000000}), encoding='utf-8')
    p = ProgressStore(file, enabled=True)
    assert p.counts['feeds'] == 0 and p.counts['taps'] == 0
    assert p.counts['stories'] == 7 and p.counts['focus_minutes'] == 0
    for evt, amount in [('window_name',1),('feeds',0),('feeds',100000),('feeds',1.5)]:
        with pytest.raises(ValueError):
            p.record(evt,amount)
    assert len(BADGES) == 7 and 'feeds' in COUNTERS


def test_settings_quotes_sanitized_and_saved(tmp_path):
    settings = Settings(progress_enabled=True, custom_quotes=['  猴山开会！  ','猴山开会！','', '\x01xyz','a'*500,123])
    settings.validated()
    assert settings.custom_quotes[:2] == ['猴山开会！', 'xyz']
    assert settings.custom_quotes[-1] == 'a'*44
    store = ConfigStore(tmp_path)
    store.save(settings)
    assert store.load() == settings
    assert Settings(custom_quotes='wrong').validated().custom_quotes == []
    settings2 = Settings(custom_quotes=[f'语录{i}' for i in range(30)]).validated()
    assert len(settings2.custom_quotes) == 12


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d:
            self.ids.add(d['id'])
        if tag in ('img','script','link'):
            self.urls.append(d.get('src', d.get('href', '')))


def test_offline_site_assets_present():
    root = Path(__file__).resolve().parents[1]
    site = root/'site/index.html'
    assert site.is_file()
    parser = AssetParser(); parser.feed(site.read_text(encoding='utf-8'))
    assert {'top','features','story','focus','safety','install','faq'}.issubset(parser.ids)
    assert {'feed','quote','storyBtn','focusBtn','heroSpeech'}.issubset(parser.ids)
    for url in parser.urls:
        if url and not url.startswith(('http://','https://','#','data:')):
            assert (site.parent/url).is_file(), f'broken offline reference: {url}'
