"""v0.14: fictional governance persistence, vote lifecycle and branch effects."""
import json
import pytest

from core.council import Seat, CouncilStory, prepare_council
from core.governance import MonkeyLaws, POLICIES, MAX_HISTORY
from core.social import GroupStory, SCENES
from core.chronicle import TRIGGERS
from core.relationships import RelationshipStore


@pytest.fixture
def laws(tmp_path):
    return MonkeyLaws(tmp_path / 'monkey_laws.json')


def test_fresh_lawbook_is_inert_and_writes_nothing(laws):
    assert not laws.file.exists()
    assert set(laws.states) == set(POLICIES)
    assert not any(laws.states.values())
    assert laws.history == []
    assert not laws.active('rocket_license')
    assert not laws.active('not_an_issue')


@pytest.mark.parametrize('issue', tuple(POLICIES))
def test_adopt_repeal_and_stalemate_with_restart(laws, issue):
    path = laws.file
    assert laws.enact(issue, 'adopted')
    assert laws.active(issue)
    assert path.is_file()
    reload = MonkeyLaws(path)
    assert reload.active(issue)
    assert reload.enact(issue, 'stalemate')
    assert reload.active(issue)  # tie NEVER revokes prior vote
    assert reload.enact(issue, 'rejected')
    assert reload.active(issue) is False
    assert MonkeyLaws(path).active(issue) is False
    assert [x['outcome'] for x in reload.history] == ['adopted','stalemate','rejected']


@pytest.mark.parametrize('issue,outcome', [
    ('banana','adopted'), ('rocket_license','xyz'),
    (None,'rejected'), ([], 'adopted'), ('banana_rules', []),
    ('banana_rules', True), ('banana_rules', None)
])
def test_invalid_policy_votes_do_not_write_file(laws, issue, outcome):
    assert laws.enact(issue, outcome) is False
    assert not laws.file.exists()


def test_storage_is_bounded_and_atomic(laws):
    for n in range(MAX_HISTORY+10):
        assert laws.enact('banana_rules', 'adopted' if n%2 else 'rejected')
    assert len(laws.history) == MAX_HISTORY
    value=json.loads(laws.file.read_text(encoding='utf-8'))
    assert value['version']==1
    assert value['states']['banana_rules'] is True
    assert len(value['history'])==MAX_HISTORY
    assert not list(laws.file.parent.glob('.monkey-laws-*'))


def test_hardened_unknown_corrupted_and_extra_json(tmp_path):
    path=tmp_path/'monkey_laws.json'
    path.write_text('malformed :(',encoding='utf-8')
    assert not MonkeyLaws(path).active('banana_rules')
    path.write_text(json.dumps({'version':1,
      'states': {'banana_rules':'yes','quiet_hours': True,'rocket_license':1,
                 'control_user_computer':True},
      'history': [{'issue':[], 'outcome':'adopted','active':True},
                  {'issue':'quiet_hours', 'outcome':'adopted','active':True},
                  {'issue':'rocket_license','outcome':'hacked','active':True}],
      'hidden': {'read_keyboard':True}}),encoding='utf-8')
    book=MonkeyLaws(path)
    assert book.active('quiet_hours')
    assert not book.active('banana_rules')
    assert not book.active('rocket_license')
    assert book.history == [{'issue':'quiet_hours','outcome':'adopted','active':True}]
    assert book.active([]) is False


def test_clearing_laws_does_not_touch_other_saved_records(tmp_path):
    file=tmp_path/'monkey_laws.json'
    relation=tmp_path/'relationships.json'
    chronicle=tmp_path/'chronicle.json'
    relation.write_text('user other monkey relationship',encoding='utf-8')
    chronicle.write_text('user other monkey chronicle',encoding='utf-8')
    laws=MonkeyLaws(file)
    laws.enact('banana_rules','adopted')
    laws.enact('rocket_license','adopted')
    laws.clear()
    assert not file.exists()
    assert not any(laws.states.values()) and not laws.history
    assert relation.read_text(encoding='utf-8')=='user other monkey relationship'
    assert chronicle.read_text(encoding='utf-8')=='user other monkey chronicle'


def test_ballot_preview_and_interrupted_scene_have_no_laws(tmp_path):
    laws=MonkeyLaws(tmp_path/'monkey_laws.json')
    members=(Seat(0,'trickster'),Seat(1,'inventor'),Seat(2,'scholar'))
    result=prepare_council('rocket_license',members)
    assert result.result == 'adopted'
    play=CouncilStory()
    assert play.start(result)
    play.advance(.3)
    play.cancel()
    assert not play.consume_completion()
    assert not laws.active('rocket_license')
    assert not laws.file.exists()


def test_vote_lifecycle_only_consumes_once_and_rocket_trial_is_finite(tmp_path):
    laws=MonkeyLaws(tmp_path/'monkey_laws.json')
    result=prepare_council('rocket_license',(
        Seat(0,'trickster'),Seat(1,'inventor'),Seat(2,'scholar')))
    scene=CouncilStory()
    assert scene.start(result)
    for _ in range(25):
        scene.advance(.4)
        if scene.finished:
            break
    assert scene.finished
    assert scene.consume_completion()
    assert laws.enact(scene.plan.issue, scene.plan.result)
    assert not scene.consume_completion()
    assert laws.active('rocket_license')
    assert len(laws.history)==1
    rocket=GroupStory()
    assert rocket.start('rocket_trial',3)
    for _ in range(25):
        rocket.advance(.4)
        if not rocket.active:
            break
    assert not rocket.active
    assert 'rocket_trial' in TRIGGERS
    assert len(SCENES['rocket_trial'])==3


def test_denied_and_repealed_trial_writes_correct_rulebook(laws):
    pro=prepare_council('rocket_license',(
        Seat(0,'trickster'),Seat(1,'inventor'),Seat(2,'scholar')))
    con=prepare_council('rocket_license',(
        Seat(0,'captain'),Seat(1,'sleepy'),Seat(2,'scholar')))
    assert pro.result=='adopted' and con.result=='rejected'
    laws.enact(pro.issue,pro.result)
    assert laws.active('rocket_license')
    laws.enact(con.issue,con.result)
    assert not laws.active('rocket_license')


def test_quiet_law_does_not_edit_real_sound_settings(laws):
    from core.config import Settings
    saved=Settings(sound=True, social_enabled=True, ambient_encounters=True)
    laws.enact('quiet_hours','adopted')
    assert laws.active('quiet_hours')
    assert saved.sound is True
    assert saved.social_enabled is True and saved.ambient_encounters is True


def test_lawbook_separate_from_relationship_changes(laws,tmp_path):
    relations=RelationshipStore(tmp_path/'relationships.json')
    plans=prepare_council('banana_rules',(
        Seat(0,'captain'),Seat(1,'scholar'),Seat(2,'shy')))
    assert plans.result=='adopted'
    laws.enact(plans.issue,plans.result)
    assert not relations.file.exists()
    assert relations.get(0,1)['interactions']==0
