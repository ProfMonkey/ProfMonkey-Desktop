"""v0.13 offline, deterministic 3-6 character society regression suite."""
from pathlib import Path
import pytest

from core.animation import load_manifest
from core.council import (
    CouncilStory, ISSUES, PERSONALITY_VIEWS, Seat,
    derive_factions, prepare_council,
)
from core.relationships import RelationshipStore

ROOT = Path(__file__).resolve().parents[1]


class Relations:
    def __init__(self, entries=None):
        self.entries = entries or {}
    def get(self, a, b):
        return self.entries.get(tuple(sorted((a, b))), {})


def seats(*styles):
    return tuple(Seat(i, p) for i, p in enumerate(styles))


def test_all_six_personalities_vote_on_three_different_issues():
    assert set(PERSONALITY_VIEWS) == {
        'scholar', 'trickster', 'sleepy', 'inventor', 'captain', 'shy'}
    assert set(ISSUES) == {'banana_rules', 'quiet_hours', 'rocket_license'}
    for views in PERSONALITY_VIEWS.values():
        assert set(views) == set(ISSUES)


@pytest.mark.parametrize('issue,personalities,expected', [
    ('banana_rules', ('scholar', 'captain', 'sleepy'), 'adopted'),
    ('banana_rules', ('trickster', 'inventor', 'scholar'), 'rejected'),
    ('rocket_license', ('captain', 'trickster', 'inventor', 'sleepy'), 'stalemate'),
    ('quiet_hours', ('scholar', 'shy', 'sleepy'), 'adopted'),
])
def test_meeting_has_majority_vote_and_not_just_random_dialogue(issue, personalities, expected):
    result = prepare_council(issue, seats(*personalities))
    assert result.result == expected
    assert len(result.votes) == len(personalities)
    assert len(result.beats) == 3
    assert all(len(beat.poses) == len(personalities) for beat in result.beats)


def test_council_is_independent_of_input_order_and_repeatable():
    attendees = (Seat(5, 'shy'), Seat(3, 'captain'), Seat(1, 'trickster'))
    first = prepare_council('quiet_hours', attendees)
    second = prepare_council('quiet_hours', attendees)
    assert first == second
    assert set(dict(first.votes)) == {1, 3, 5}
    assert first.votes[0][0] == 5
    assert all(0 <= i < 6 for i, _ in first.votes)


def test_all_actions_exist_in_original_manifest():
    actions = set(load_manifest(ROOT/'assets/monkey/manifest.json'))
    for issue in ISSUES:
        plan = prepare_council(issue, seats(*PERSONALITY_VIEWS))
        for beat in plan.beats:
            assert .5 <= beat.seconds <= 5
            assert len({idx for idx, _action, _line in beat.poses}) == 6
            for _index, action, line in beat.poses:
                assert action in actions
                assert line
                assert len(line) <= 60


@pytest.mark.parametrize('issue,group', [
    ('unknown', seats('scholar', 'captain', 'sleepy')),
    ('quiet_hours', seats('scholar', 'sleepy')),
    ('quiet_hours', (Seat(0,'scholar'), Seat(0,'captain'), Seat(1,'sleepy'))),
    ('quiet_hours', (Seat(True,'scholar'), Seat(1,'captain'), Seat(2,'sleepy'))),
    ('quiet_hours', (Seat(-1,'scholar'), Seat(1,'captain'), Seat(2,'sleepy'))),
    ('quiet_hours', seats('banana', 'captain', 'sleepy')),
])
def test_invalid_meetings_rejected(issue, group):
    with pytest.raises(ValueError):
        prepare_council(issue, group)


def test_friendship_influences_vote_and_enmity_can_counteract():
    team = seats('sleepy', 'trickster', 'captain')
    neutral = prepare_council('banana_rules', team)
    friends = Relations({(0,2): dict(bond=80, trust=80)})
    rivals = Relations({(0,2): dict(rivalry=80)})
    assert prepare_council('banana_rules', team, friends) != neutral
    assert prepare_council('banana_rules', team, rivals) != neutral


def test_factions_emerge_and_reconfigure_from_relationships():
    group = seats('scholar', 'captain', 'inventor', 'trickster', 'sleepy', 'shy')
    assert derive_factions(group) == ()
    edges = Relations({
        (0, 1): {'bond': 40, 'trust': 35},
        (1, 2): {'bond': 38, 'trust': 30},
        (3, 4): {'bond': 60, 'trust': 70},
    })
    assert derive_factions(group, edges) == ((0,1,2), (3,4))
    edges.entries[(1,2)]['rivalry'] = 60
    assert derive_factions(group, edges) == ((0,1), (3,4))
    edges.entries[(0,1)]['bond'] = 15
    assert derive_factions(group, edges) == ((3,4),)


def test_faction_ids_are_valid_and_free_of_duplicates():
    with pytest.raises(ValueError):
        derive_factions((Seat(0,'scholar'), Seat(0,'trickster')))
    with pytest.raises(ValueError):
        derive_factions((Seat(True,'scholar'),))


def test_timed_three_beat_story_can_interrupt_without_finishing():
    plan = prepare_council('banana_rules', seats('scholar','captain','sleepy'))
    timeline = CouncilStory()
    assert timeline.start(plan)
    assert not timeline.start(plan)
    assert timeline.index == 0
    assert timeline.beat == plan.beats[0]
    timeline.advance(.4)
    timeline.cancel()
    assert not timeline.active
    assert not timeline.finished
    assert timeline.start(plan)
    for beat in range(3):
        for _ in range(20):
            if timeline.index > beat:
                break
            timeline.advance(.4)
        assert timeline.index == beat + 1
    assert timeline.finished and timeline.beat is None
    assert timeline.consume_completion()
    assert not timeline.consume_completion()
    assert timeline.advance(.4) is False
    timeline.cancel()
    assert timeline.beat is None
    assert not timeline.consume_completion()
    with pytest.raises(ValueError):
        timeline.advance(-.01)
    with pytest.raises(ValueError):
        timeline.advance(.6)
    with pytest.raises(ValueError):
        timeline.advance(float('nan'))


def test_ballot_is_atomic_and_once_for_every_non_abstaining_pair(tmp_path):
    path = tmp_path / 'relationships.json'
    rel = RelationshipStore(path)
    assert not path.exists()
    votes = ((0,'yes'), (1,'yes'), (2,'no'), (3,'abstain'))
    rel.record_council(votes)
    assert path.exists()
    assert rel.get(0,1)['bond'] == 2
    assert rel.get(0,1)['trust'] == 2
    assert rel.get(0,1)['interactions'] == 1
    assert rel.get(0,2)['rivalry'] == 2
    assert rel.get(1,2)['bond'] == -1
    assert rel.get(0,3)['interactions'] == 0
    loaded = RelationshipStore(path)
    assert loaded.get(0,1) == rel.get(0,1)


@pytest.mark.parametrize('invalid', [
    ((0,'yes'),(1,'yes')),  # too few
    ((0,'yes'),(0,'no'),(1,'yes')),
    ((True,'yes'),(1,'no'),(2,'yes')),
    ((0,'yes'),(1,'banana'),(2,'no')),
    ((0,'yes'),(1,'no'),(8,'yes')),
    [(0,'yes'),(1,'yes'),(2,'yes')],
])
def test_invalid_ballot_writes_nothing(tmp_path, invalid):
    file = tmp_path / 'relationships.json'
    rel = RelationshipStore(file)
    with pytest.raises(ValueError):
        rel.record_council(invalid)
    assert not file.exists()


def test_council_effects_eventually_create_true_alliances(tmp_path):
    rel = RelationshipStore(tmp_path/'relationships.json')
    group = seats('scholar', 'captain', 'shy')
    assert derive_factions(group, rel) == ()
    for _ in range(18):
        rel.record_council(((0,'yes'),(1,'yes'),(2,'yes')))
    assert derive_factions(group, rel) == ((0,1,2),)
    rel.record_council(((0,'yes'),(1,'no'),(2,'yes')))
    assert rel.get(0,1)['rivalry'] >= 2
