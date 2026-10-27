"""v0.11 core regression suite: personality chemistry, scenes and opt-in safety."""
import pytest

from core.config import ConfigStore, Settings
from core.duo_story import DuoStory
from core.encounters import EncounterDirector, Participant
from core.profiles import PERSONALITIES, clean_profiles
from core.state import Brain, PetState


class Relations:
    def __init__(self, **scores):
        self.scores = scores

    def get(self, _a, _b):
        return self.scores


def pairing(first, second, *, relation=None):
    # Manual demo ignores distance and timing but respects character busy state.
    director = EncounterDirector(seed=5)
    return director.choose(0, [
        Participant(0, 100, 300, first),
        Participant(1, 800, 300, second),
    ], Relations(**(relation or {})), force=True)


def test_six_personalities_are_available_and_default_profiles_distinct():
    assert tuple(PERSONALITIES) == ('scholar', 'trickster', 'sleepy', 'inventor', 'captain', 'shy')
    assert [p['personality'] for p in clean_profiles(None)] == list(PERSONALITIES)
    assert len({p['name'] for p in clean_profiles(None)}) == 6


@pytest.mark.parametrize('first,second,kind', [
    ('scholar', 'inventor', 'invention'),
    ('captain', 'trickster', 'inspection'),
    ('captain', 'sleepy', 'roll_call'),
    ('shy', 'trickster', 'boundary'),
    ('shy', 'scholar', 'library'),
    ('sleepy', 'inventor', 'sleep_machine'),
    ('inventor', 'captain', 'launch'),
])
def test_both_role_orders_produce_correct_pair_story(first, second, kind):
    for a, b in ((first, second), (second, first)):
        event = pairing(a, b)
        assert event.kind == kind
        assert event.personality_first == a
        assert event.personality_second == b
        assert len(event.line_first) > 6
        duo = DuoStory()
        assert duo.start(event)
        duo.advance(.4)
        while duo.index == 0:
            duo.advance(.4)
        end = duo.beat
        assert end.first != end.second
        if kind == 'roll_call':
            assert ('请假条' in end.first[1]) == (a == 'sleepy')
        duo.cancel()
        assert not duo.active


def test_relationship_overrides_personality_pairing():
    assert pairing('captain', 'trickster', relation={'rivalry': 60}).kind == 'debate'
    assert pairing('captain', 'trickster', relation={'bond': 70, 'trust': 60}).kind == 'high_five'


def test_story_stays_alive_until_second_beat_and_may_be_cancelled():
    episode = DuoStory()
    event = pairing('captain', 'sleepy')
    assert episode.start(event)
    assert not episode.start(event)
    assert episode.beat.first[1] == event.line_first
    assert episode.advance(.4) is False
    episode.cancel()
    assert not episode.active and episode.beat is None
    assert episode.start(event)
    changed = False
    for _ in range(7):
        changed = episode.advance(.4) or changed
    assert changed and episode.index == 1
    assert episode.finished is False
    for _ in range(6):
        episode.advance(.4)
    assert episode.finished and episode.event == event
    assert episode.advance(.4) is False
    episode.cancel()
    assert not episode.finished and episode.index == 0
    with pytest.raises(ValueError):
        episode.advance(-.1)
    with pytest.raises(ValueError):
        episode.advance(.6)


def test_six_brains_are_seeded_and_have_distinct_preferences():
    sequences = []
    for personality in PERSONALITIES:
        def sequence():
            brain, state = Brain(seed=12, personality=personality), PetState(mode='MONKEY')
            return [brain.next(state, 6) for _ in range(80)]
        assert sequence() == sequence()
        sequences.append(tuple(sequence()))
    assert len(set(sequences)) == 6


def test_profile_settings_persist_without_input_tracking(tmp_path):
    store = ConfigStore(tmp_path)
    profiles = [{'name': '成员' + str(i), 'personality': p} for i, p in enumerate(PERSONALITIES)]
    store.save(Settings(monkey_count=6, monkey_profiles=profiles,
                        ambient_encounters=True, input_tracking=True))
    saved = store.load()
    assert saved.monkey_profiles == profiles
    assert saved.ambient_encounters
    assert saved.input_tracking is False
    assert Settings().validated().ambient_encounters is False


def test_busy_monkeys_never_start_a_manual_scene():
    d = EncounterDirector()
    assert d.choose(0, [Participant(0, 0, 0, 'captain', True),
                         Participant(1, 2, 0, 'trickster')], Relations(), force=True) is None
