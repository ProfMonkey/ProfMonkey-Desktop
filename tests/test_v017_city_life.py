"""v0.17 regression tests: branching city mysteries, save compatibility and atomicity."""
from dataclasses import replace
import json
import pytest

from core.civilization import BUILDINGS
from core.city_life import (CASE_CHOICES, CASE_TITLES, CASE_CHAPTERS,
    CASE_EFFECTS, CASE_CHOICES, MAX_CASE_NEWS, CityLifeStory, empty_case,
    normalize_cases, prepare_city_case)
from core.expeditions import ExpeditionJournal, newspaper


def setup_buildings(tmp_path, required=('banana_vault',)):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    journal.resources.update(bananas=130,science=130,reputation=130)
    for key in BUILDINGS:
        if key in required:
            assert journal.construct(key)
    return journal


@pytest.mark.parametrize('case',tuple(CASE_TITLES))
def test_each_case_has_three_distinct_chapters_and_two_choices(case):
    assert len(CASE_CHAPTERS[case])==3
    assert len(CASE_CHOICES[case])==2
    assert set(CASE_EFFECTS[case])=={'careful','bold'}
    assert all(len(line)==3 for line in CASE_CHAPTERS[case])
    assert not any(not text for chapter in CASE_CHAPTERS[case] for text in chapter)


def test_new_city_has_unwritten_inert_cases(tmp_path):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    assert not journal.path.exists()
    assert set(journal.city_cases)==set(CASE_TITLES)
    assert journal.city_news==[]
    assert all(row==empty_case() for row in journal.city_cases.values())


def test_unbuilt_structure_cannot_gain_resource_or_case_progress(tmp_path):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    plan=prepare_city_case('banana_vault',empty_case(),0,1,'careful')
    assert not journal.record_city_chapter(plan)
    assert not journal.path.exists()


def test_episode_plays_all_three_beats_and_only_one_completion(tmp_path):
    journal=setup_buildings(tmp_path)
    before=journal.resources.copy()
    plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                           0,1,'careful')
    story=CityLifeStory()
    assert story.start(plan)
    assert not story.start(plan)
    assert not story.consume_completion()
    story.advance(.2)
    assert not story.consume_completion()
    story.cancel()
    assert journal.resources==before
    assert journal.city_cases['banana_vault']['chapter']==0
    assert story.start(plan)
    for _ in range(30):
        if story.finished:
            break
        story.advance(.4)
    assert story.finished
    assert story.beat is None
    assert story.consume_completion()
    assert not story.consume_completion()
    assert journal.record_city_chapter(story.plan)
    assert journal.resources['bananas']==before['bananas']-1
    assert journal.resources['reputation']==before['reputation']+2
    assert journal.city_cases['banana_vault']['chapter']==1
    assert not journal.record_city_chapter(plan)
    story.cancel()
    assert not story.consume_completion()
    assert len(journal.city_news)==1


def test_three_careful_choices_resolve_case_and_persist(tmp_path):
    journal=setup_buildings(tmp_path)
    for index in range(3):
        plan=prepare_city_case('banana_vault',
            journal.city_cases['banana_vault'],0,1,'careful')
        assert plan.chapter==index
        assert journal.record_city_chapter(plan)
        assert not journal.record_city_chapter(plan)
    status=journal.city_cases['banana_vault']
    assert status=={'chapter':3,'careful':3,'bold':0,'ending':'reconciled'}
    assert '温暖结局' in newspaper(journal)
    fresh=ExpeditionJournal(journal.path)
    assert fresh.city_cases['banana_vault']==status
    assert len(fresh.city_news)==3
    with pytest.raises(ValueError):
        prepare_city_case('banana_vault',status,0,1,'careful')


def test_three_bold_choices_cause_fictional_dispute(tmp_path):
    journal=setup_buildings(tmp_path)
    for _ in range(3):
        plan=prepare_city_case('banana_vault',
            journal.city_cases['banana_vault'],0,1,'bold')
        assert journal.record_city_chapter(plan)
    assert journal.city_cases['banana_vault']['ending']=='chaos'
    assert journal.city_cases['banana_vault']['bold']==3


def test_friendship_can_resolve_a_mixed_finale(tmp_path):
    journal=setup_buildings(tmp_path)
    for choice in ('bold','bold'):
        plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                               0,1,choice)
        assert journal.record_city_chapter(plan)
    final=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                            0,1,'careful',bond=50,trust=35)
    assert final.ending=='reconciled'
    without=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                              0,1,'careful',bond=0,trust=0)
    assert without.ending=='chaos'


def test_cases_persist_in_same_atomic_city_file(tmp_path,monkeypatch):
    journal=setup_buildings(tmp_path)
    before=journal.resources.copy()
    plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                           0,1,'bold')
    saves=[]
    original=journal._save
    def count():
        saves.append('save')
        return original()
    monkeypatch.setattr(journal,'_save',count)
    assert journal.record_city_chapter(plan)
    assert saves==['save']
    fresh=ExpeditionJournal(journal.path)
    assert fresh.city_cases['banana_vault']['chapter']==1
    assert fresh.resources['bananas']==before['bananas']+1
    assert fresh.resources['reputation']==before['reputation']-1


def test_disk_failure_restores_all_in_memory_fields(tmp_path,monkeypatch):
    journal=setup_buildings(tmp_path)
    before=journal.resources.copy()
    old_case=journal.city_cases['banana_vault'].copy()
    old_news=list(journal.city_news)
    plan=prepare_city_case('banana_vault',old_case,0,1,'careful')
    def disk_full():
        raise OSError('disk full')
    monkeypatch.setattr(journal,'_save',disk_full)
    assert not journal.record_city_chapter(plan)
    assert journal.resources==before
    assert journal.city_cases['banana_vault']==old_case
    assert journal.city_news==old_news


def test_corrupted_progress_invalid_ending_ignored(tmp_path):
    journal=setup_buildings(tmp_path)
    path=journal.path
    payload=json.loads(path.read_text(encoding='utf-8'))
    payload['city_cases']={'banana_vault':{'chapter':3,'careful':2,'bold':1,'ending':''}}
    payload['city_news']=[
        {'case':'banana_vault','chapter':True,'choice':'bold','ending':''},
        {'case':[],'chapter':1,'choice':'bold','ending':''},
        {'case':'banana_vault','chapter':1,'choice':'careful','ending':''},
    ]
    path.write_text(json.dumps(payload),encoding='utf-8')
    reloaded=ExpeditionJournal(path)
    assert reloaded.city_cases['banana_vault']==empty_case()
    assert len(reloaded.city_news)==1


def test_untrusted_cases_never_unlock_unbuilt_building(tmp_path):
    path=tmp_path/'expeditions.json'
    path.write_text(json.dumps({'version':1,'buildings':[],
       'city_cases':{'monkey_academy':{
           'chapter':3,'careful':3,'bold':0,'ending':'reconciled'}},
       'city_news':[{'case':'monkey_academy','chapter':3,'choice':'careful',
                    'ending':'reconciled'}]}),encoding='utf-8')
    journal=ExpeditionJournal(path)
    assert not journal.buildings
    assert journal.city_cases['monkey_academy']==empty_case()
    assert not journal.city_news


@pytest.mark.parametrize('bad_choice', ['fake',None,[],False])
def test_unknown_branch_refuses_to_play(bad_choice):
    with pytest.raises(ValueError):
        prepare_city_case('banana_vault',empty_case(),0,1,bad_choice)


def test_illegal_roles_refused():
    for a,b in ((0,0),(-1,1),(0,6),(True,1)):
        with pytest.raises(ValueError):
            prepare_city_case('public_square',empty_case(),a,b,'careful')


def test_repeated_old_plan_cannot_farm_rewards(tmp_path):
    journal=setup_buildings(tmp_path)
    plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                           0,1,'bold')
    assert journal.record_city_chapter(plan)
    balance=journal.resources.copy()
    for _ in range(20):
        assert not journal.record_city_chapter(plan)
    assert journal.resources==balance
    assert journal.city_cases['banana_vault']['chapter']==1


def test_not_enough_banana_never_goes_negative(tmp_path):
    journal=setup_buildings(tmp_path)
    journal.resources['bananas']=0
    plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                           0,1,'careful')
    assert journal.record_city_chapter(plan)
    assert journal.resources['bananas']==0


def test_clear_city_removes_cases_but_preserves_other_records(tmp_path):
    journal=setup_buildings(tmp_path)
    plan=prepare_city_case('banana_vault',journal.city_cases['banana_vault'],
                           0,1,'careful')
    assert journal.record_city_chapter(plan)
    other=tmp_path/'relationships.json'
    other.write_text('keep this',encoding='utf-8')
    journal.clear()
    assert journal.city_news==[]
    assert journal.city_cases['banana_vault']==empty_case()
    assert not journal.path.exists()
    assert other.read_text(encoding='utf-8')=='keep this'


def test_selected_monkey_personalities_have_distinct_dialogue():
    professor = prepare_city_case(
        'banana_vault', empty_case(), 0, 1, 'careful',
        first_personality='scholar', second_personality='trickster')
    inventor = prepare_city_case(
        'banana_vault', empty_case(), 0, 1, 'careful',
        first_personality='inventor', second_personality='captain')
    assert professor.beats[1].poses[0][2] != inventor.beats[1].poses[0][2]
    assert professor.beats[1].poses[1][2] != inventor.beats[1].poses[1][2]
    assert professor.resource_delta == inventor.resource_delta


def test_city_map_reports_pending_chapter_and_completed_case(tmp_path):
    from core.civilization import city_report
    journal = setup_buildings(tmp_path)
    summary = city_report(journal.buildings, journal.resources,
                          journal.city_cases)
    assert '第1章待演出' in summary
    for _ in range(3):
        p = prepare_city_case('banana_vault',
                              journal.city_cases['banana_vault'], 0, 1, 'careful')
        assert journal.record_city_chapter(p)
    finished = city_report(journal.buildings, journal.resources,
                           journal.city_cases)
    assert '✅ 结案' in finished
