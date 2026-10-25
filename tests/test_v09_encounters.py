from core.encounters import EncounterDirector, Participant


class Relations:
    def __init__(self, **attrs):
        self.attrs = attrs
    def get(self, first, second):
        return self.attrs


def pets(a=0, b=70, *, mood='scholar'):
    return [Participant(0, a, 550, mood), Participant(1, b, 550, 'trickster')]


def test_nearby_monkeys_greet_then_cooldown():
    director = EncounterDirector(seed=4)
    first = director.choose(0, pets(), Relations())
    assert first is not None
    assert first.first == 0 and first.second == 1
    assert director.choose(10, pets(), Relations()) is None
    assert director.choose(130, pets(), Relations()) is None  # pair is still cooling
    assert director.choose(241, pets(), Relations()) is not None


def test_no_event_when_too_far_or_busy():
    director = EncounterDirector()
    assert director.choose(10, pets(0, 200), Relations()) is None
    busy = [Participant(0, 0, 550, 'scholar', True), Participant(1, 12, 550, 'trickster')]
    assert director.choose(10, busy, Relations()) is None


def test_manual_demo_bypasses_distance_not_busy():
    director = EncounterDirector(seed=4)
    assert director.choose(0, pets(0, 700), Relations(), force=True)
    assert director.choose(1, pets(0, 700), Relations(), force=True)


def test_friend_and_rival_have_distinct_scripts():
    friend = EncounterDirector().choose(0, pets(), Relations(bond=70, trust=80))
    rival = EncounterDirector().choose(0, pets(), Relations(rivalry=70))
    assert friend.kind == 'high_five'
    assert rival.kind == 'debate'
    assert '香蕉' in rival.line_second


def test_sleepy_greeting_and_deterministic_selection():
    a = EncounterDirector(seed=19).choose(0, pets(mood='sleepy'), Relations())
    b = EncounterDirector(seed=19).choose(0, pets(mood='sleepy'), Relations())
    assert a == b
    assert a.kind == 'nap'


def test_three_monkeys_chooses_closest_pair():
    team = pets(0, 80) + [Participant(2, 85, 550, 'scholar')]
    event = EncounterDirector().choose(0, team, Relations())
    assert (event.first, event.second) == (1, 2)


def test_clear_releases_cooldowns():
    director = EncounterDirector()
    assert director.choose(0, pets(), Relations())
    director.clear()
    assert director.choose(0, pets(), Relations())


def test_encounters_are_opt_in_and_persisted(tmp_path):
    from core.config import ConfigStore, Settings
    store = ConfigStore(tmp_path)
    assert store.load().ambient_encounters is False
    store.save(Settings(ambient_encounters=True, monkey_count=2))
    assert store.load().ambient_encounters is True
    assert store.load().monkey_count == 2

def test_no_automatic_global_input_capture_default():
    from core.config import Settings
    s = Settings(input_tracking=True).validated()
    assert s.input_tracking is False
