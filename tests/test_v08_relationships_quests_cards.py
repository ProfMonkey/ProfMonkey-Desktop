from datetime import date, timedelta
from pathlib import Path
from PIL import Image
import pytest

from core.relationships import RelationshipStore
from core.quests import QuestBoard
from core.story_card import STORIES, render_story_card
from core.profiles import clean_profiles

ROOT = Path(__file__).resolve().parents[1]


def test_relationship_memory_updates_and_survives_restart(tmp_path):
    path = tmp_path / 'relationships.json'
    store = RelationshipStore(path)
    assert store.get(0, 1)['label'] == '普通同事'
    store.record_meeting([0, 1, 2])
    first = store.get(0, 1)
    assert first['bond'] == 3 and first['trust'] == 2
    store.record_race(0, 1)
    assert store.get(0, 1)['rivalry'] == 5
    store.set_mentor(0, 1)
    loaded = RelationshipStore(path)
    assert loaded.get(0, 1) == store.get(0, 1)
    assert loaded.mentor_of(1) == 0


def test_relationship_rejects_self_and_invalid_indices(tmp_path):
    store = RelationshipStore(tmp_path / 'relations.json')
    with pytest.raises(ValueError):
        store.get(2, 2)
    with pytest.raises(ValueError):
        store.set_mentor(9, 1)


def test_relationship_values_are_bounded(tmp_path):
    store = RelationshipStore(tmp_path / 'relations.json')
    for _ in range(100):
        store.record_race(0, 1)
    rel = store.get(0, 1)
    assert rel['rivalry'] == 100
    assert rel['bond'] == -100
    assert rel['trust'] == 0
    assert rel['label'] == '死对头'
    store.reconcile(0, 1)
    assert store.get(0, 1)['rivalry'] == 92


def test_daily_quests_rotate_and_award_only_once(tmp_path):
    board = QuestBoard(tmp_path / 'quests.json', today=date(2026, 10, 25))
    assert board.active_ids == ('feed', 'story', 'group')
    assert board.record('feed', today=date(2026, 10, 25))
    assert board.record('story', today=date(2026, 10, 25))
    assert board.record('group', today=date(2026, 10, 25))
    snap = board.snapshot(2, today=date(2026, 10, 25))
    assert snap['all_complete'] and snap['points'] == 3
    assert not board.record('group', today=date(2026, 10, 25))
    loaded = QuestBoard(tmp_path / 'quests.json', today=date(2026, 10, 25))
    assert loaded.snapshot(2, today=date(2026, 10, 25))['points'] == 3
    next_day = loaded.snapshot(2, today=date(2026, 10, 25))
    assert next_day['all_complete'] is True


def test_daily_quest_rolls_over_on_new_day(tmp_path):
    path = tmp_path / 'quests.json'
    board = QuestBoard(path, today=date(2026, 10, 25))
    board.record('feed', today=date(2026, 10, 25))
    tomorrow = QuestBoard(path, today=date(2026, 10, 26))
    snap = tomorrow.snapshot(1, today=date(2026, 10, 26))
    assert snap['date'] == '2026-10-26'
    assert all(task['progress'] == 0 for task in snap['tasks'])
    assert any(task['locked'] for task in snap['tasks'])


def test_story_card_is_created_from_local_art_only(tmp_path):
    output = tmp_path / 'story.png'
    profiles = clean_profiles([{'name': '猴教授', 'personality': 'scholar'},
                               {'name': '香蕉主任', 'personality': 'trickster'}])
    size = render_story_card(ROOT / 'assets/monkey/idle.png', profiles, 2, 'banana_duel', output)
    assert size == (1200, 800)
    with Image.open(output) as image:
        assert image.format == 'PNG'
        assert image.size == size
    assert output.stat().st_size > 10_000


def test_story_card_rejects_unknown_story_and_count(tmp_path):
    with pytest.raises(ValueError):
        render_story_card(ROOT / 'assets/monkey/idle.png', [], 7, 'banana', tmp_path / 'bad.png')
    with pytest.raises(ValueError):
        render_story_card(ROOT / 'assets/monkey/idle.png', [], 1, 'unknown', tmp_path / 'bad.png')


def test_daily_quest_invalid_event_does_not_change_state(tmp_path):
    board = QuestBoard(tmp_path / 'quests.json', today=date(2026, 10, 25))
    assert not board.record('read_keyboard')
    assert board.snapshot(2)['points'] == 0
