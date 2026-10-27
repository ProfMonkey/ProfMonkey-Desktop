"""v0.19 read-only monkey society and opt-in autonomous behavior regressions."""
from dataclasses import replace
import json
import pytest
from core.civic_society import (
    CivicSnapshot, FACTIONS, city_society, civic_action_bias, civic_encounter,
    society_report,
)
from core.expeditions import ExpeditionJournal
from core.city_life import prepare_city_case
from core.city_evolution import prepare_evolution
from core.config import Settings, ConfigStore
from core.encounters import EncounterDirector, Participant
from core.state import Brain, PetState


class Laws:
    def __init__(self, *names):
        self.names = set(names)

    def active(self, key):
        return key in self.names


class Relations:
    def __init__(self, bond=0, trust=0, rivalry=0):
        self.value = dict(bond=bond, trust=trust, rivalry=rivalry)

    def get(self, a, b):
        return dict(self.value)


def build(tmp_path, *buildings):
    journal = ExpeditionJournal(tmp_path/'expeditions.json')
    journal.resources.update(bananas=180, science=180, reputation=180)
    for name in ('banana_vault', 'galaxy_scope', 'public_square',
                 'monkey_academy'):
        if name in buildings:
            assert journal.construct(name)
    return journal


def close_case(journal, name, choice):
    for _ in range(3):
        assert journal.record_city_chapter(prepare_city_case(
            name, journal.city_cases[name], 0, 1, choice))


def test_off_by_default_and_persistent_in_old_config(tmp_path):
    store = ConfigStore(tmp_path)
    initial = store.load()
    assert initial.civic_autonomy is False
    store.save(Settings(civic_autonomy=True))
    assert store.load().civic_autonomy is True
    store.save(Settings(civic_autonomy=False))
    assert store.load().civic_autonomy is False


def test_zero_buildings_means_zero_behavior_bias_and_no_disk_writes(tmp_path):
    journal = ExpeditionJournal(tmp_path/'expeditions.json')
    before = journal.resources.copy()
    snapshot = city_society(journal, count=2)
    assert snapshot.era.endswith('萌芽时代')
    assert all(m.building is None for m in snapshot.members)
    assert all(civic_action_bias(m, snapshot) == (0,)*6
               for m in snapshot.members)
    assert journal.resources == before
    assert not journal.path.exists()
    assert '自由探险者' in society_report(snapshot)


def test_jobs_depend_on_owned_buildings_and_personality(tmp_path):
    journal = build(tmp_path,'banana_vault','galaxy_scope')
    profiles = [{'name':'教授', 'personality':'scholar'},
                {'name':'发明师', 'personality':'inventor'},
                {'name':'队长', 'personality':'captain'}]
    snapshot = city_society(journal, profiles=profiles, count=3)
    assert [m.building for m in snapshot.members] == [
        'galaxy_scope', 'galaxy_scope', 'banana_vault']
    assert snapshot.members[0].name == '教授'
    assert civic_action_bias(snapshot.members[0],snapshot)[2] > 0
    assert civic_action_bias(snapshot.members[2],snapshot)[1] > 0


def test_legacy_history_and_laws_have_detectable_social_consequences(tmp_path):
    journal = build(tmp_path,'banana_vault')
    close_case(journal,'banana_vault','careful')
    prior = city_society(journal, count=2)
    assert journal.record_evolution(prepare_evolution('granary','community',journal))
    after = city_society(journal, Laws('banana_rules'), count=2)
    assert after.cooperation > prior.cooperation
    assert after.tension < prior.tension
    assert '钥匙制度' in society_report(after)
    again = city_society(journal,Laws('banana_rules'),count=2)
    assert after == again


def test_bold_history_changes_innovation_and_tension(tmp_path):
    journal = build(tmp_path,'galaxy_scope')
    close_case(journal,'galaxy_scope','bold')
    before = city_society(journal,count=2)
    assert journal.record_evolution(prepare_evolution('star_chart','elite',journal))
    after = city_society(journal,count=2)
    assert after.innovation > before.innovation
    assert after.tension > before.tension
    assert after.meeting_probability < before.meeting_probability


def test_faction_lines_depend_on_personalities_and_history(tmp_path):
    journal = build(tmp_path,'banana_vault')
    profiles = [{'name':'学究','personality':'scholar'},
                {'name':'皮猴','personality':'trickster'}]
    snapshot = city_society(journal,profiles=profiles,count=2)
    assert snapshot.members[0].faction == 'community'
    assert snapshot.members[1].faction == 'pioneer'
    assert FACTIONS[snapshot.members[0].faction] != FACTIONS[snapshot.members[1].faction]


def test_relationships_affect_citywide_climate(tmp_path):
    journal = build(tmp_path,'public_square')
    base = city_society(journal,count=2)
    stronger = city_society(journal,relationships=Relations(50,50,0),count=2)
    rivals = city_society(journal,relationships=Relations(-40,0,90),count=2)
    assert stronger.cooperation > base.cooperation
    assert rivals.tension > base.tension


def test_invalid_monkey_count_rejected(tmp_path):
    journal = ExpeditionJournal(tmp_path/'e.json')
    for bad in (-1,0,7,True,'6'):
        with pytest.raises(ValueError):
            city_society(journal,count=bad)


def test_animation_brain_has_no_behavior_change_before_opt_in():
    a=Brain(seed=194)
    b=Brain(seed=194)
    assert a.civic_bias == (0,)*6
    for _ in range(30):
        s1=PetState(mode='MONKEY')
        s2=PetState(mode='MONKEY')
        assert a.next(s1, 5.) == b.next(s2, 5.)
    a.set_civic_bias((4,0,3,0,0,0))
    assert a.civic_bias[0] == 4
    a.set_civic_bias(None)
    assert a.civic_bias == (0,)*6
    for value in ((-1,)*6,(100,)*6,('x',)*6,(0,)*5,True):
        with pytest.raises(ValueError):
            a.set_civic_bias(value)


def test_civic_encounter_uses_existing_pair_and_completion_types(tmp_path):
    journal = build(tmp_path,'banana_vault','galaxy_scope','public_square')
    snapshot = city_society(journal,count=2)
    director = EncounterDirector(max_distance=100)
    people = [Participant(0,0,0,'scholar'),Participant(1,10,10,'trickster')]
    expected = director.choose(100,people,None,force=True,civic=snapshot)
    assert expected.kind.startswith('civic_')
    assert expected.first == 0 and expected.second == 1
    assert expected.outcome_first is not None
    assert expected.outcome_second is not None
    from core.duo_story import DuoStory
    scene = DuoStory()
    assert scene.start(expected)
    # Second act has own history follow-up, never the legacy hello fallback.
    for _ in range(6):
        scene.advance(.5)
    assert scene.beat.first == expected.outcome_first
    assert scene.beat.second == expected.outcome_second
    # Legacy engine is unaffected by a null civic context.
    old = EncounterDirector(max_distance=100).choose(100,people,None,force=True)
    assert not old.kind.startswith('civic_')


def test_unbuilt_empty_world_falls_back_to_original_dialogue(tmp_path):
    journal = ExpeditionJournal(tmp_path/'e.json')
    snapshot = city_society(journal,count=2)
    a,b = Participant(0,0,0,'scholar'),Participant(1,0,0,'trickster')
    assert civic_encounter(a,b,{},snapshot) is None


def test_clashing_factions_can_generate_proper_dispute(tmp_path):
    journal = build(tmp_path,'banana_vault','galaxy_scope')
    snapshot = city_society(journal,count=2)
    members = (replace(snapshot.members[0],faction='community'),
               replace(snapshot.members[1],faction='pioneer'))
    strained = replace(snapshot,tension=90,members=members)
    a,b = Participant(0,0,0,'scholar'),Participant(1,0,0,'trickster')
    dialogue = civic_encounter(a,b,{'rivalry':80},strained)
    assert dialogue.kind == 'civic_dispute'
    assert dialogue.action_first == 'angry'


def test_derived_society_never_changes_city_records(tmp_path):
    journal = build(tmp_path,'banana_vault')
    raw_before = journal.path.read_bytes()
    balance_before = journal.resources.copy()
    news_before = list(journal.city_news)
    snapshot = city_society(journal,Laws('quiet_hours'),Relations(40,30,0),count=6)
    _ = society_report(snapshot)
    assert journal.path.read_bytes() == raw_before
    assert journal.resources == balance_before
    assert journal.city_news == news_before
