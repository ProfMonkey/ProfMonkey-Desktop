"""v0.12: reproducible offline branching stories, growth and storage boundaries."""
import json
import pytest

from core.chronicle import (
    CHAPTERS, GOOD_ENDING, CHAOS_ENDING, MAX_CASES, MAX_EVENTS,
    ChronicleStore, TITLES, TRIGGERS,
)
from core.config import ConfigStore, Settings
from core.duo_story import DuoStory
from core.encounters import Encounter


def perform(store, case_id, relation=None):
    scene = store.preview(case_id, relation)
    assert scene is not None
    event = Encounter(scene.first, scene.second, 'chronicle',
                      scene.opening[0][0], scene.opening[1][0],
                      scene.opening[0][1], scene.opening[1][1],
                      outcome_first=scene.ending[0], outcome_second=scene.ending[1])
    duo = DuoStory()
    assert duo.start(event)
    assert duo.beat.first == scene.opening[0]
    assert duo.beat.second == scene.opening[1]
    for _ in range(12):
        duo.advance(.4)
        if duo.finished:
            break
    assert duo.finished
    assert duo.beat is not None
    # Full second-beat staging must match the authored scene.
    duo.index = 1
    assert duo.beat.first == scene.ending[0]
    assert duo.beat.second == scene.ending[1]
    assert store.complete(scene)
    duo.cancel()
    return scene


def test_default_off_does_not_write_anything(tmp_path):
    path = tmp_path / 'chronicle.json'
    store = ChronicleStore(path)
    assert store.observe('banana_duel', 0, 1) is None
    assert store.pending() == []
    assert not path.exists()
    assert store.growth_for(0)['level'] == 1


@pytest.mark.parametrize('trigger,kind', sorted(TRIGGERS.items()))
def test_event_can_open_an_opted_in_three_chapter_case(tmp_path, trigger, kind):
    path = tmp_path / 'book.json'
    store = ChronicleStore(path, enabled=True)
    cid = store.observe(trigger, 0, 1)
    assert cid == 1
    assert store.pending()[0]['title'] == TITLES[kind]
    assert store.observe(trigger, 1, 0) is None  # same unresolved case
    assert store.observe('not_an_event', 0, 1) is None
    assert path.exists()
    for index in (0, 1):
        assert store.growth_for(index)['level'] == 1
    assert len(CHAPTERS[kind]) == 2
    for index in range(2):
        result = perform(store, cid)
        assert result.chapter == index and result.branch == 'continuing'
        assert store.preview(cid).chapter == index + 1
    final = perform(store, cid)
    assert final.chapter == 2 and final.branch == 'chaos'
    assert store.preview(cid) is None and store.pending() == []
    assert store.growth_for(0)['level'] == 1  # 3 scenes < first threshold (4)
    assert store.growth_for(0)['title'] != '见习猴'
    assert len(store.events) == 4  # open + 3 completed
    assert ChronicleStore(path, enabled=True).preview(cid) is None


def test_final_chapter_chooses_reconciliation_when_trust_is_high(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    cid = store.observe('meeting', 2, 4)
    perform(store, cid)
    perform(store, cid)
    alt = store.preview(cid)
    success = store.preview(cid, {'trust': 50, 'bond': 20})
    assert alt.branch == 'chaos'
    assert success.branch == 'good'
    assert success.ending != alt.ending
    assert store.complete(success)
    assert store.growth_for(2)['research'] == 3
    assert store.growth_for(4)['research'] == 3


def test_cancelled_duo_does_not_advance_chronicle(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    cid = store.observe('launch', 0, 3)
    scene = store.preview(cid)
    event = Encounter(0, 3, 'chronicle', scene.opening[0][0], scene.opening[1][0],
                      scene.opening[0][1], scene.opening[1][1],
                      outcome_first=scene.ending[0], outcome_second=scene.ending[1])
    duo = DuoStory()
    assert duo.start(event)
    duo.advance(.4)
    duo.cancel()
    assert store.preview(cid) == scene
    assert store.growth_for(0)['research'] == 0
    assert [e['event'] for e in store.events] == ['opened']


def test_duplicate_and_forged_completion_are_rejected(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    cid = store.observe('roll_call', 1, 4)
    scene = store.preview(cid)
    assert store.complete(scene)
    assert store.complete(scene) is False
    assert store.events[-1]['chapter'] == 1
    from dataclasses import replace
    assert store.complete(replace(store.preview(cid), first=3)) is False
    assert store.complete(replace(store.preview(cid), ending=(('run', 'fake'), ('idle', 'fake')))) is False
    assert store.growth_for(1)['empathy'] == 1


def test_opt_out_disables_progress_and_existing_cases_remain_private(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    cid = store.observe('banana_duel', 0, 1)
    scene = store.preview(cid)
    store.enabled = False
    assert store.pending() == []
    assert store.preview(cid) is None
    assert store.complete(scene) is False
    assert store.observe('meeting', 2, 3) is None
    store.enabled = True
    assert store.preview(cid) == scene
    assert store.complete(scene) is True


def test_member_count_filters_hidden_stories_and_no_accidental_reassignment(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    cid = store.observe('banana_duel', 3, 5)
    assert store.pending(member_count=2) == []
    assert store.pending(member_count=6)[0]['id'] == cid
    assert store.preview(cid) is not None
    for bad in [(-1, 2), (3, 3), (True, 3), ('0', 3), (0, 6)]:
        assert store.observe('meeting', *bad) is None


def test_case_cap_does_not_evict_open_cases(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    # Four different storylines per unique pair give at least 12 distinct cases.
    pairs = [(a, b) for a in range(6) for b in range(a+1, 6)]
    for a, b in pairs[:MAX_CASES]:
        assert store.observe('banana_duel', a, b)
    assert len(store.pending()) == MAX_CASES
    assert store.observe('meeting', 0, 1) is None
    assert len(store.cases) == MAX_CASES


def test_bounded_events_and_growth_points(tmp_path):
    store = ChronicleStore(tmp_path / 'book.json', enabled=True)
    for _ in range(MAX_EVENTS+15):
        store._log(dict(case_id=1, kind='banana', chapter=1, event='completed'))
    assert len(store.events) == MAX_EVENTS
    cid = store.observe('banana_duel', 0, 1)
    for _ in range(3):
        perform(store, cid)
    assert len(store.events) == MAX_EVENTS


def test_restart_preserves_progress_without_replaying_awards(tmp_path):
    path = tmp_path / 'book.json'
    old = ChronicleStore(path, enabled=True)
    cid = old.observe('invention', 2, 5)
    perform(old, cid)
    new = ChronicleStore(path, enabled=True)
    assert new.preview(cid).chapter == 1
    assert new.growth_for(2)['research'] == 1
    assert new.observe('launch', 5, 2) is None  # no duplicate rocket case
    perform(new, cid)
    assert new.growth_for(5)['research'] == 2


def test_clear_removes_file_but_not_unrelated_records(tmp_path):
    path = tmp_path / 'chronicle.json'
    unrelated = tmp_path / 'relationships.json'
    unrelated.write_text('keep me', encoding='utf-8')
    store = ChronicleStore(path, enabled=True)
    store.observe('meeting', 0, 1)
    store.clear()
    assert not path.exists() and unrelated.read_text(encoding='utf-8') == 'keep me'
    assert store.pending() == [] and store.growth_for(0)['title'] == '见习猴'


def test_untrusted_json_is_sanitized_and_never_used_as_prose(tmp_path):
    path = tmp_path / 'chronicle.json'
    path.write_text(json.dumps({
        'version': 1, 'next_id': True,
        'cases': [
            {'id': 'bad', 'kind': 'banana', 'first': 0, 'second': 1, 'stage': 0},
            {'id': 9, 'kind': 'banana', 'first': 0, 'second': 0, 'stage': 0},
            {'id': 8, 'kind': 'banana', 'first': 0, 'second': 1, 'stage': 2},
            {'id': 8, 'kind': 'exam', 'first': 3, 'second': 4, 'stage': 0},
        ],
        'growth': {'0': {'research': 999999, 'mischief': -9, 'empathy': 'hack'},
                   '__class__': {'research': 5}},
        'events': [{'event': 'keyboard_capture', 'kind': 'banana', 'case_id': 8, 'chapter': 0}],
        'extra': {'copy_desktop': True},
    }), encoding='utf-8')
    store = ChronicleStore(path, enabled=True)
    assert len(store.cases) == 1 and store.cases[0]['id'] == 8
    assert store.next_id == 9
    assert store.events == []
    assert store.growth_for(0)['research'] == 9999
    assert store.growth_for(0)['mischief'] == 0


def test_settings_default_disabled_and_roundtrip(tmp_path):
    config = ConfigStore(tmp_path)
    assert Settings().validated().chronicle_enabled is False
    config.save(Settings(chronicle_enabled=True, input_tracking=True))
    reloaded = config.load()
    assert reloaded.chronicle_enabled is True
    assert reloaded.input_tracking is False
