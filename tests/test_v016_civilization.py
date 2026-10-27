"""Pure-Python v0.16 city construction, atomic economy and expedition regressions."""
from dataclasses import replace
import json
import pytest

from core.civilization import (BUILDINGS, construction_status, sanitize_city,
                               city_tier, city_report, mission_city_bonus)
from core.expeditions import (ExpeditionJournal, Explorer, plan_expedition,
                              newspaper, BLUEPRINTS)


def roster(*names):
    return tuple(Explorer(i, s) for i, s in enumerate(names))


def affluent(tmp_path):
    book=ExpeditionJournal(tmp_path/'expeditions.json')
    book.resources.update(bananas=90,science=90,reputation=90)
    return book


def test_new_city_off_by_default_and_prices_are_explicit(tmp_path):
    book=ExpeditionJournal(tmp_path/'expeditions.json')
    assert not book.path.exists()
    assert book.buildings==frozenset()
    assert len(BUILDINGS)==4
    assert city_tier(book.buildings)==(0, '🌱 初生猴山')
    assert not book.construct('banana_vault')
    assert not book.path.exists()
    assert construction_status('banana_vault',book.resources,book.buildings)[0] is False


def test_basic_construction_is_one_payment_then_persistent(tmp_path):
    book=affluent(tmp_path)
    assert book.construct('banana_vault')
    assert book.resources=={'bananas':78,'science':90,'reputation':90}
    assert book.buildings==frozenset({'banana_vault'})
    assert not book.construct('banana_vault')
    assert book.resources['bananas']==78
    clone=ExpeditionJournal(book.path)
    assert clone.buildings==book.buildings
    assert clone.resources==book.resources
    assert len(clone.unlocked())>=1
    assert '香蕉研究仓库' in newspaper(clone)


def test_academy_requires_all_three_base_districts(tmp_path):
    journal=affluent(tmp_path)
    assert not journal.construct('monkey_academy')
    for key in ('banana_vault','galaxy_scope','public_square'):
        assert journal.construct(key)
    assert city_tier(journal.buildings)[0]==3
    assert journal.construct('monkey_academy')
    assert journal.buildings==frozenset(BUILDINGS)
    assert city_tier(journal.buildings)==(4,'🌌 银河猴山文明')
    assert journal.resources=={'bananas':58,'science':58,'reputation':58}


@pytest.mark.parametrize('mission,crew,building,expected_score,expected_rewards',[
    ('banana_scout',('trickster','inventor'),'banana_vault',6,(6,1,1)),
    ('meteor_lab',('scholar','inventor'),'galaxy_scope',7,(0,6,2)),
    ('village_repair',('captain','shy'),'public_square',7,(1,1,6)),
])
def test_constructed_building_changes_real_mission_result(
        mission,crew,building,expected_score,expected_rewards):
    plan=plan_expedition(mission,roster(*crew),built=frozenset({building}))
    assert plan.score==expected_score
    assert plan.rewards==expected_rewards
    assert plan.city_buildings==frozenset({building})


def test_academy_general_bonus_applies_to_all_missions(tmp_path):
    journal=affluent(tmp_path)
    for key in BUILDINGS:
        assert journal.construct(key)
    for mission in ('banana_scout','meteor_lab','village_repair'):
        without=plan_expedition(mission,roster('trickster','inventor'))
        with_city=plan_expedition(mission,roster('trickster','inventor'),
                                  built=journal.buildings)
        assert with_city.score==without.score+2
    assert '银河猴山文明' in city_report(journal.buildings,journal.resources)


def test_laws_and_city_rewards_stack_once_at_departure(tmp_path):
    book=affluent(tmp_path)
    assert book.construct('banana_vault')
    plan=plan_expedition('banana_scout',roster('trickster','inventor'),
        active_laws=frozenset({'banana_rules'}),built=book.buildings)
    assert plan.outcome=='success'
    assert plan.rewards==(7,1,1)
    assert book.record(plan)
    assert book.resources['bananas']==85  # 78 + 7
    assert book.resources['science']==91
    assert book.resources['reputation']==91


def test_city_snapshot_does_not_retroactively_change_active_mission(tmp_path):
    book=affluent(tmp_path)
    plan=plan_expedition('banana_scout',roster('trickster','inventor'))
    assert plan.outcome=='mixed' and plan.rewards==(2,0,1)
    assert book.construct('banana_vault')
    assert book.record(plan)
    assert book.resources['bananas']==80 # 90 - 12 + 2
    assert plan.city_buildings==frozenset()
    newer=plan_expedition('banana_scout',roster('trickster','inventor'),
                          built=book.buildings)
    assert newer.outcome=='success' and newer.rewards==(6,1,1)


def test_city_ownership_survives_old_v015_save_without_field(tmp_path):
    path=tmp_path/'expeditions.json'
    path.write_text(json.dumps({'version':1,
     'resources':{'bananas':23,'science':15,'reputation':1},
     'missions':{'0':5},'log':[]}),encoding='utf-8')
    book=ExpeditionJournal(path)
    assert book.buildings==frozenset()
    assert book.resources['bananas']==23
    assert book.construct('banana_vault')
    reloaded=ExpeditionJournal(path)
    assert reloaded.buildings==frozenset({'banana_vault'})
    assert reloaded.resources['bananas']==11
    assert reloaded.missions[0]==5


def test_corrupt_city_data_and_unmet_academy_are_ignored(tmp_path):
    path=tmp_path/'expeditions.json'
    path.write_text(json.dumps({'version':1,
      'resources':{'bananas':40,'science':40,'reputation':40},
      'buildings':['banana_vault','monkey_academy','unknown',True,{'id':'public_square'}]}),
      encoding='utf-8')
    loaded=ExpeditionJournal(path)
    assert loaded.buildings==frozenset({'banana_vault'})
    assert loaded.resources['bananas']==40
    assert sanitize_city(['monkey_academy'])==frozenset()
    with pytest.raises(ValueError):
        plan_expedition('banana_scout',roster('scholar','inventor'),
                        built=frozenset({'monkey_academy'}))


def test_invalid_and_duplicate_build_never_change_balances_or_disk(tmp_path):
    journal=affluent(tmp_path)
    before=dict(journal.resources)
    assert not journal.construct('unknown')
    assert not journal.construct(None)
    assert not journal.construct([])
    assert not journal.construct('monkey_academy')
    assert journal.resources==before
    assert not journal.path.exists()


def test_building_purchase_rolls_back_on_save_error(tmp_path,monkeypatch):
    journal=affluent(tmp_path)
    original=dict(journal.resources)
    def fail():
        raise OSError('disk full')
    monkeypatch.setattr(journal,'_save',fail)
    assert not journal.construct('banana_vault')
    assert journal.resources==original
    assert not journal.buildings
    assert not journal.path.exists()


def test_one_atomic_save_per_purchase(tmp_path,monkeypatch):
    journal=affluent(tmp_path)
    real_save=journal._save
    calls=[]
    def counted():
        calls.append(1)
        real_save()
    monkeypatch.setattr(journal,'_save',counted)
    assert journal.construct('galaxy_scope')
    assert calls==[1]
    assert not list(tmp_path.glob('.expedition-*'))


def test_saving_and_reopening_complete_city(tmp_path):
    journal=affluent(tmp_path)
    for key in BUILDINGS:
        assert journal.construct(key)
    loaded=ExpeditionJournal(journal.path)
    assert loaded.buildings==journal.buildings
    assert loaded.resources==journal.resources
    assert set(k for k,_ in loaded.unlocked())==set(BUILDINGS)
    assert len(BLUEPRINTS)==4


def test_clearing_city_together_with_resource_book_is_explicit(tmp_path):
    book=affluent(tmp_path)
    outside=tmp_path/'monkey_laws.json'
    outside.write_text('preserve laws',encoding='utf-8')
    assert book.construct('banana_vault')
    book.clear()
    assert not book.buildings
    assert book.resources=={'bananas':0,'science':0,'reputation':0}
    assert not book.path.exists()
    assert outside.read_text(encoding='utf-8')=='preserve laws'


def test_reward_plan_rejects_forged_city_extra_resources(tmp_path):
    journal=affluent(tmp_path)
    plan=plan_expedition('banana_scout',roster('trickster','inventor'))
    fake=replace(plan,rewards=(888,0,1))
    assert not journal.record(fake)
    assert not journal.path.exists()
    assert journal.resources['bananas']==90


def test_valid_city_bonus_cannot_include_fake_achievement():
    score,bonus=mission_city_bonus('banana_scout',frozenset(), 'success')
    assert score==0 and bonus==(0,0,0)
