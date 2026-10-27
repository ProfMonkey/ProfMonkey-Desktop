"""Pure-Python regression coverage for fictional expeditions, without CI."""
import json
import pytest
from core.expeditions import (
    BLUEPRINTS, ExpeditionJournal, ExpeditionStory, Explorer, MISSIONS,
    RESOURCE_KEYS, MAX_LOG, plan_expedition, newspaper
)


class Relationships:
    def __init__(self, values):
        self.values = values
    def get(self, a, b):
        return self.values.get(tuple(sorted((a, b))), {})


def crew(*kinds):
    return tuple(Explorer(i, kind) for i, kind in enumerate(kinds))


@pytest.mark.parametrize('mission,members,result,rewards', [
    ('banana_scout',('trickster','inventor'),'mixed',(2,0,1)),
    ('meteor_lab',('scholar','inventor'),'success',(0,5,2)),
    ('village_repair',('captain','shy'),'success',(1,1,5)),
    ('banana_scout',('sleepy','sleepy'),'mishap',(0,0,0)),
])
def test_distinct_character_skills_change_outcome(mission,members,result,rewards):
    plan=plan_expedition(mission,crew(*members))
    assert plan.outcome==result
    assert plan.rewards==rewards
    assert len(plan.beats)==3
    assert all(len(beat.poses)==len(members) for beat in plan.beats)
    assert all(.5<=beat.seconds<=5. for beat in plan.beats)
    assert len({index for index,_,_ in plan.beats[0].poses})==len(members)


@pytest.mark.parametrize('mission,policy,team,rewards', [
    ('banana_scout','banana_rules',('trickster','inventor'),(6,1,1)),
    ('meteor_lab','rocket_license',('scholar','inventor'),(0,6,2)),
    ('village_repair','quiet_hours',('captain','shy'),(1,1,6)),
])
def test_snapshotted_council_laws_have_real_mission_effects(
        mission,policy,team,rewards):
    plan=plan_expedition(mission,crew(*team),
                         active_laws=frozenset({policy}))
    assert plan.outcome=='success'
    assert plan.law_boost and plan.rewards==rewards
    assert plan_expedition(mission,crew(*team)).law_boost is False


def test_friendship_can_make_the_same_team_succeed_and_rivalry_hurts():
    team=crew('trickster','shy')
    neutral=plan_expedition('banana_scout',team)
    friendly=plan_expedition('banana_scout',team,
        Relationships({(0,1): {'bond':50,'trust':40,'rivalry':0}}))
    rivals=plan_expedition('banana_scout',team,
        Relationships({(0,1): {'bond':-50,'trust':1,'rivalry':80}}))
    assert neutral.score==5 and neutral.outcome=='mixed'
    assert friendly.score==6 and friendly.outcome=='success'
    assert rivals.score==4 and rivals.outcome=='mixed'


@pytest.mark.parametrize('mission,team', [
    ('invalid',crew('scholar','inventor')),
    ('banana_scout',crew('inventor')),
    ('banana_scout',(Explorer(0,'scholar'),Explorer(0,'inventor'))),
    ('banana_scout',(Explorer(True,'scholar'),Explorer(1,'inventor'))),
    ('banana_scout',(Explorer(0,'scholar'),Explorer(7,'inventor'))),
    ('banana_scout',(Explorer(0,'robot'),Explorer(1,'inventor'))),
    ([],crew('scholar','inventor')),
])
def test_invalid_and_duplicate_teams_are_rejected(mission,team):
    with pytest.raises(ValueError):
        plan_expedition(mission,team)


def test_story_cancels_without_awarding_and_completes_only_once(tmp_path):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    mission=plan_expedition('meteor_lab',crew('inventor','scholar'))
    story=ExpeditionStory()
    assert story.start(mission)
    story.advance(.4)
    story.cancel()
    assert not story.consume_completion()
    assert not journal.path.exists()
    assert story.start(mission)
    for step in range(3):
        for _ in range(20):
            if story.index>step:
                break
            story.advance(.4)
        assert story.index==step+1
    assert story.finished and story.beat is None
    assert story.consume_completion() and not story.consume_completion()
    assert journal.record(story.plan)
    assert journal.resources['science']==5
    assert journal.missions[0]==1 and journal.missions[1]==1
    assert len(journal.log)==1
    story.cancel()
    assert not story.consume_completion()
    with pytest.raises(ValueError):
        story.advance(-.01)
    with pytest.raises(ValueError):
        story.advance(float('nan'))


def test_completed_expedition_persists_and_restores(tmp_path):
    path=tmp_path/'expeditions.json'
    journal=ExpeditionJournal(path)
    assert not path.exists()
    plan=plan_expedition('banana_scout',crew('trickster','inventor'),
                         active_laws=frozenset({'banana_rules'}))
    assert journal.record(plan)
    assert journal.resources['bananas']==6
    clone=ExpeditionJournal(path)
    assert clone.resources==journal.resources
    assert clone.missions==journal.missions
    assert clone.log==journal.log
    assert len(clone.unlocked())==0
    assert newspaper(clone).count('香蕉')>=1


def test_unlocks_are_derived_from_resources_not_paid_with_money(tmp_path):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    a=plan_expedition('banana_scout',crew('trickster','inventor'),
                      active_laws=frozenset({'banana_rules'}))
    b=plan_expedition('meteor_lab',crew('scholar','inventor'),
                      active_laws=frozenset({'rocket_license'}))
    c=plan_expedition('village_repair',crew('captain','shy'),
                      active_laws=frozenset({'quiet_hours'}))
    for _ in range(4):
        for mission in (a,b,c):
            assert journal.record(mission)
    assert {key for key,_ in journal.unlocked()}=={key for key,_,_ in BLUEPRINTS}
    assert journal.resources=={'bananas':28,'science':32,'reputation':36}
    # Nothing has been spent or redeemed from outside the program.
    assert all(isinstance(n,int) for n in journal.resources.values())


def test_bounded_resources_counts_log_and_atomic_file(tmp_path):
    journal=ExpeditionJournal(tmp_path/'expeditions.json')
    plan=plan_expedition('banana_scout',crew('trickster','inventor'),
                         active_laws=frozenset({'banana_rules'}))
    for _ in range(250):
        journal.record(plan)
    assert journal.resources['bananas']==999
    assert len(journal.log)==MAX_LOG
    assert journal.missions[0]==250
    assert not list(tmp_path.glob('.expedition-*'))


def test_corrupted_json_never_loads_arbitrary_fields(tmp_path):
    path=tmp_path/'expeditions.json'
    path.write_text(json.dumps({
        'version':1,
        'resources':{'bananas':999999,'science':'hack','reputation':-2},
        'missions':{'0':90000,'1':True,'__class__':9999},
        'log':[
            {'mission':[], 'crew':[0,1], 'outcome':'success'},
            {'mission':'banana_scout','crew':[0,0], 'outcome':'success'},
            {'mission':'banana_scout','crew':[0,1], 'outcome':'success'},
            {'mission':'meteor_lab','crew':['0',1], 'outcome':'mixed'}],
        'readDesktop':True
    }),encoding='utf-8')
    store=ExpeditionJournal(path)
    assert store.resources=={'bananas':999,'science':0,'reputation':0}
    assert store.missions[0]==999 and store.missions[1]==0
    assert store.log==[{'mission':'banana_scout','outcome':'success','crew':[0,1]}]


def test_clear_only_erases_missions_not_relationships(tmp_path):
    p=tmp_path/'expeditions.json'
    other=tmp_path/'relationships.json'
    other.write_text('keep original user monkey relationships',encoding='utf-8')
    journal=ExpeditionJournal(p)
    journal.record(plan_expedition('meteor_lab',crew('scholar','inventor')))
    journal.clear()
    assert not p.exists()
    assert sum(journal.resources.values())==0 and not journal.log
    assert other.read_text(encoding='utf-8')=='keep original user monkey relationships'


def test_local_newspaper_only_describes_in_app_data(tmp_path):
    j=ExpeditionJournal(tmp_path/'book.json')
    j.record(plan_expedition('meteor_lab',crew('scholar','inventor')))
    text=newspaper(j,names=('学究猴','发明猴'))
    assert '学究猴' in text and '发明猴' in text
    assert '陨石研究所' in text
    assert '科研' in text


def test_multi_monkey_relation_awards_use_one_atomic_save(tmp_path, monkeypatch):
    from core.relationships import RelationshipStore
    path=tmp_path/'relationships.json'
    relations=RelationshipStore(path)
    old_save=relations._save
    writes=[]
    def save():
        writes.append('one')
        old_save()
    monkeypatch.setattr(relations,'_save',save)
    relations.record_expedition((0,1,2,3,4,5),'success')
    assert writes==['one']
    assert len(relations.pairs)==15
    assert relations.get(0,5)['bond']==3
    assert relations.get(0,5)['trust']==2
    assert relations.get(0,5)['interactions']==1
    relations.record_expedition((0,1),'mixed')
    assert writes==['one','one']
    assert relations.get(0,1)['bond']==5
    relations.record_expedition((0,1),'mishap')
    assert relations.get(0,1)['rivalry']==2


@pytest.mark.parametrize('invalid_team,result',[
    ((0,), 'success'), ((0,0),'success'), ((0,9),'mixed'),
    ((True,1),'success'), ([0,1],'success'), ((0,1),'fabricated')
])
def test_invalid_relation_team_never_writes_a_file(tmp_path, invalid_team, result):
    from core.relationships import RelationshipStore
    path=tmp_path/'relationships.json'
    relation=RelationshipStore(path)
    with pytest.raises(ValueError):
        relation.record_expedition(invalid_team,result)
    assert not path.exists()
