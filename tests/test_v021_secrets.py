"""Six hidden stories: user-led clues, branch integrity, actual three-beat
completion, bounded save semantics and no unauthorized background actions.
No Qt, internet, screen recording, login, Actions or personal data needed.
"""
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from core.secrets import (
    SECRET_CASES, GESTURES, LIMITS, SecretJournal, SecretStory,
    prepare_secret
)
from core.profiles import clean_profiles


@pytest.fixture
def context():
    return SimpleNamespace(
        buildings=frozenset(('banana_vault','galaxy_scope','public_square',
                             'monkey_academy')),
        city_cases={
            'galaxy_scope':{'chapter':2},
            'monkey_academy':{'chapter':1}
        },
        legacy_events=[{'event':'constitution','route':'community'}],
    )


def make(tmp_path):
    j=SecretJournal(tmp_path/'secrets_v021.json')
    # Prepare all gesture prerequisites without saving any user data.
    j.gestures.update(feeds=3,rapid_taps=2,races=1,mirrors=1)
    return j


def cast(story):
    profiles=clean_profiles([])
    lead=SECRET_CASES[story]['lead']
    first=next(i for i,p in enumerate(profiles) if p['personality']==lead)
    return profiles,first,(first+1)%6


def test_exactly_six_character_led_three_chapter_cases():
    assert len(SECRET_CASES)==6
    assert {m['lead'] for m in SECRET_CASES.values()}=={
        'scholar','trickster','sleepy','inventor','captain','shy'}
    assert all(len(m['chapters'])==3 for m in SECRET_CASES.values())
    for item in SECRET_CASES.values():
        assert len(item['truth'])>20
        assert len(item['secret'])>20
        assert all(len(scene)==3 for scene in item['chapters'])


def test_preview_never_creates_a_file(tmp_path):
    j=SecretJournal(tmp_path/'s.json')
    assert not j.path.exists()
    profiles=clean_profiles([])
    ok,hint=j.unlocked('banana_receipt',2,profiles)
    assert not ok and '3' in hint
    assert not j.path.exists()


def test_gestures_only_explicit_and_bounded(tmp_path):
    j=SecretJournal(tmp_path/'s.json')
    assert not j.observe_gesture('bogus')
    assert not j.observe_gesture(None)
    assert not j.path.exists()
    for gesture,key in GESTURES.items():
        for index in range(LIMITS[key]):
            assert j.observe_gesture(gesture)==(index==LIMITS[key]-1)
        assert not j.observe_gesture(gesture)
        assert j.gestures[key]==LIMITS[key]
    saved=json.loads(j.path.read_text(encoding='utf-8'))
    assert saved['gestures']==j.gestures
    other=SecretJournal(j.path)
    assert other.gestures==j.gestures


def test_unlock_gates_use_actual_existing_game_context(tmp_path,context):
    j=SecretJournal(tmp_path/'s.json')
    profiles=clean_profiles([])
    # Event-specific old city decisions are deliberately separate from gesture
    # easter eggs; some cases are discoverable immediately in an established city.
    for case_id in ('banana_receipt','shadow_07','sleep_strike'):
        assert not j.unlocked(case_id,6,profiles,context)[0]
    for case_id in ('signal_404','button_zero','last_ballot'):
        assert j.unlocked(case_id,6,profiles,context)[0]
    j.gestures.update(feeds=3,rapid_taps=2,races=1,mirrors=1)
    for case_id in SECRET_CASES:
        assert j.unlocked(case_id,6,profiles,context)[0],case_id
    context.buildings=frozenset()
    assert not j.unlocked('signal_404',6,profiles,context)[0]
    assert not j.unlocked('button_zero',6,profiles,context)[0]
    assert j.unlocked('banana_receipt',6,profiles,context)[0]
    assert not j.unlocked('shadow_07',5,profiles,context)[0]


@pytest.mark.parametrize('case_id',tuple(SECRET_CASES))
def test_six_stories_three_chapters_two_branches_and_finite_3_beats(tmp_path,context,case_id):
    journal=make(tmp_path)
    profiles,a,b=cast(case_id)
    for chapter,route in enumerate(('reveal','hide','reveal')):
        plan=prepare_secret(journal,case_id,a,b,route,6,profiles,context)
        assert plan.chapter==chapter
        assert len(plan.beats)==3
        assert all(len(beat.poses)==2 and beat.seconds>0 for beat in plan.beats)
        assert plan.beats[0].poses[0][0]==a
        assert plan.beats[1].poses[1][0]==b
        game=SecretStory()
        assert game.start(plan)
        assert not game.consume_completion()
        for step in range(3):
            assert game.beat is not None
            while not game.advance(.25):
                pass
        assert game.finished and game.consume_completion()
        assert not game.consume_completion()
        assert journal.record(plan,6,profiles,context)
        assert not journal.record(plan,6,profiles,context)
        game.cancel()
        assert not game.active
    assert journal.cases[case_id]['chapter']==3
    assert journal.cases[case_id]['reveal']==2
    assert journal.cases[case_id]['hide']==1
    assert journal.cases[case_id]['ending']=='unmasked'
    assert len(journal.news)==3
    reloaded=SecretJournal(journal.path)
    assert reloaded.cases[case_id]==journal.cases[case_id]
    with pytest.raises(ValueError):
        prepare_secret(journal,case_id,a,b,'reveal',6,profiles,context)


def test_repeated_hiding_yields_ambiguity_not_public_resolution(tmp_path,context):
    j=make(tmp_path)
    profiles,a,b=cast('shadow_07')
    for route in ('hide','hide','reveal'):
        plan=prepare_secret(j,'shadow_07',a,b,route,6,profiles,context)
        assert j.record(plan,6,profiles,context)
    assert j.cases['shadow_07']['ending']=='unresolved'


def test_wrong_actor_route_crew_and_spoofed_plan_rejected(tmp_path,context):
    j=make(tmp_path)
    profiles,a,b=cast('button_zero')
    with pytest.raises(ValueError):
        prepare_secret(j,'button_zero',b,a,'reveal',6,profiles,context)
    for bad in ('bad','REVEAL',None):
        with pytest.raises(ValueError):
            prepare_secret(j,'button_zero',a,b,bad,6,profiles,context)
    for bad in (a,True,10,-1):
        with pytest.raises(ValueError):
            prepare_secret(j,'button_zero',a,bad,'reveal',6,profiles,context)
    plan=prepare_secret(j,'button_zero',a,b,'reveal',6,profiles,context)
    assert not j.record(replace(plan,ending='unmasked'),6,profiles,context)
    assert not j.record(replace(plan,chapter=2),6,profiles,context)
    assert not j.record(replace(plan,beats=()),6,profiles,context)
    assert j.cases['button_zero']['chapter']==0


def test_no_effect_when_story_cancelled_before_third_beat(tmp_path,context):
    j=make(tmp_path)
    profiles,a,b=cast('signal_404')
    plan=prepare_secret(j,'signal_404',a,b,'reveal',6,profiles,context)
    story=SecretStory()
    assert story.start(plan)
    story.advance(.25)
    story.cancel()
    assert not story.consume_completion()
    assert j.cases['signal_404']['chapter']==0
    assert not j.path.exists()


def test_transaction_rollback_on_write_error(tmp_path,context,monkeypatch):
    j=make(tmp_path)
    profiles,a,b=cast('banana_receipt')
    p=prepare_secret(j,'banana_receipt',a,b,'reveal',6,profiles,context)
    def failure():raise OSError('disk full')
    monkeypatch.setattr(j,'_save',failure)
    assert not j.record(p,6,profiles,context)
    assert j.cases['banana_receipt']['chapter']==0
    assert j.news==[]
    assert not j.observe_gesture('feed')  # counter was saturated already


def test_corrupt_or_unknown_save_cannot_inject_unlocked_endings(tmp_path):
    p=tmp_path/'evil.json'
    p.write_text(json.dumps({'version':1,
        'gestures':{'feeds':True,'rapid_taps':9999,'mirrors':-1},
        'cases':{'banana_receipt':{'chapter':3,'reveal':0,'hide':0,'ending':'unmasked'},
                 'shadow_07':{'chapter':1,'reveal':1,'hide':0,'ending':'unmasked'}},
        'news':[{'case':'not a case','chapter':9,'route':'reveal'}]}),
        encoding='utf-8')
    j=SecretJournal(p)
    assert j.gestures['feeds']==0
    assert j.gestures['rapid_taps']==0
    assert j.cases['banana_receipt']['chapter']==0
    assert j.cases['shadow_07']['chapter']==0
    assert not j.news


def test_clear_only_secrets_and_preserve_other_user_records(tmp_path,context):
    j=make(tmp_path)
    profiles,a,b=cast('banana_receipt')
    p=prepare_secret(j,'banana_receipt',a,b,'reveal',6,profiles,context)
    assert j.record(p,6,profiles,context)
    other=tmp_path/'relationships.json'
    other.write_text('SENTINEL',encoding='utf-8')
    j.clear()
    assert all(row['chapter']==0 for row in j.cases.values())
    assert all(v==0 for v in j.gestures.values())
    assert other.read_text()=='SENTINEL'

def test_secret_finale_requires_six_complete_cases(tmp_path,context):
    j=make(tmp_path)
    assert j.epilogue() is None
    for case_id in SECRET_CASES:
        profiles,a,b=cast(case_id)
        for route in ('reveal','reveal','hide'):
            plan=prepare_secret(j,case_id,a,b,route,6,profiles,context)
            assert j.record(plan,6,profiles,context)
    assert j.epilogue() is not None
    assert '第七位见证者' in j.epilogue()
    assert len(j.news)==18
    j.clear()
    assert j.epilogue() is None
