"""Headless behavioral tests: profiles, stage integrity, portrait privacy."""
from pathlib import Path
from PIL import Image
import pytest

from core.config import ConfigStore, Settings
from core.profiles import clean_profiles, clean_name
from core.social import GroupStory, SCENES
from core.portrait import render_colony_portrait
from core.state import Brain, PetState

ROOT=Path(__file__).resolve().parents[1]


def test_profile_cleanup_preserves_all_six_even_with_one_pet():
    values=clean_profiles([{'name':'  猴教授\n恶作剧\u202e', 'personality':'unknown'},
                           {'name':'R' * 40, 'personality':'trickster'}])
    assert len(values)==6
    assert values[0]['name']=='猴教授恶作剧'
    assert values[0]['personality']=='scholar'
    assert values[1]=={'name':'R'*12, 'personality':'trickster'}
    assert clean_name(' \t ',3)=='香蕉主任'
    assert clean_profiles([{'personality': []}])[0]['personality']=='scholar'


def test_settings_round_trip_and_no_tracking(tmp_path):
    store=ConfigStore(tmp_path)
    values=[{'name':'猴子'+str(i), 'personality':'sleepy'} for i in range(6)]
    store.save(Settings(monkey_count=6,monkey_profiles=values,social_enabled=True,
                        input_tracking=True))
    output=store.load()
    assert output.monkey_count==6
    assert output.monkey_profiles==values
    assert output.social_enabled is True
    assert output.input_tracking is False


def test_group_stories_finish_and_no_overlap():
    for name in SCENES:
        director=GroupStory()
        assert not director.start(name,1)
        assert director.start(name,2)
        assert not director.start(name,3)
        assert director.beat is not None
        steps=0
        while director.active:
            director.advance(.1)
            steps+=1
            assert steps<500
        assert director.beat is None
        assert director.index==0
    with pytest.raises(ValueError):
        GroupStory().advance(-1)


def test_group_stories_have_supported_actions():
    from core.animation import load_manifest
    available=set(load_manifest(ROOT/'assets/monkey/manifest.json'))
    for scene in SCENES.values():
        assert 3 <= len(scene) <= 6
        assert sum(item.seconds for item in scene)<=20
        for stage in scene:
            assert 0 < stage.seconds < 10
            for action, line in (stage.first,stage.second,stage.others):
                assert action in available
                assert line


def test_personalities_produce_reproducible_distinct_behavior():
    def seq(p):
        brain=Brain(seed=123,personality=p)
        state=PetState(mode='MONKEY')
        results=[]
        for _ in range(70):
            results.append(brain.next(state,10))
        return results
    assert seq('scholar')==seq('scholar')
    assert seq('scholar')!=seq('trickster')
    assert seq('sleepy')!=seq('trickster')


@pytest.mark.parametrize('n',[1,2,3,4,6])
def test_group_portrait_uses_only_local_sprites(tmp_path, n):
    output=tmp_path / f'portrait-{n}.png'
    profiles=clean_profiles([{'name':'核桃','personality':'trickster'}])
    assert render_colony_portrait(ROOT/'assets/monkey/idle.png',profiles,n,output)==(1000,660)
    with Image.open(output) as im:
        assert im.size==(1000,660)
        assert im.format=='PNG'
        assert im.getpixel((0,0)) != im.getpixel((400,300))
    assert output.stat().st_size>5000


def test_portrait_rejects_invalid_count(tmp_path):
    with pytest.raises(ValueError):
        render_colony_portrait(ROOT/'assets/monkey/idle.png',[],7,tmp_path/'test.png')


def test_colony_settings_defaults_are_safe_and_opt_out_of_tracking():
    settings = Settings().validated()
    assert settings.colony_behavior == 'free'
    assert settings.collisions_enabled is True
    assert settings.input_tracking is False
