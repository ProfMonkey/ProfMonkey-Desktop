"""Tests for integrated behavior and privacy-safe persistence."""
from pathlib import Path
import json
import math
import pytest
from core.physics import Body
from core.state import Brain, PetState
from core.config import ConfigStore, Settings
from core.events import StoryDirector
from core.history import History
from core.export import export_action_gif, export_story_gif


def test_bouncing_limits_and_floor():
    b = Body(x=88,y=20,vx=800,vy=-400,airborne=True)
    for _ in range(400):
        b.step(.02, (0,0,200,120), (50,50))
        assert 0 <= b.x <= 150
        assert 0 <= b.y <= 70
    assert b.y == 70 and not b.airborne


def test_physics_throw_speed_capped_and_invalid_time():
    b = Body(); b.throw(8000,-9000)
    assert (b.vx,b.vy)==(950,-950)
    with pytest.raises(ValueError): b.step(float('nan'),(0,0,100,100),(10,10))


def test_energy_sleep_recovers_and_walk_costs():
    a = PetState(energy=50,action='sleep')
    a.tick(2)
    assert a.energy == 60
    a.action='walk';a.tick(2)
    assert a.energy < 60


def test_seeded_brain_reproducible():
    def sample():
        b=Brain(9912);s=PetState()
        choices=[]
        for _ in range(150):
            x=b.next(s,.4)
            if x:choices.append(x)
            s.tick(.4)
        return choices
    assert sample() == sample()
    assert len(sample()) >= 5


def test_causal_banana_two_endings_cleanup():
    for safe in (True,False):
        finished=[]
        d=StoryDirector(on_finish=finished.append)
        assert d.start('banana',safe=safe)
        assert not d.start('mirror')
        seen=[]
        for _ in range(150):
            if d.beat: seen.append(d.beat.action)
            d.advance(.2)
        assert not d.active
        assert finished == ['banana_safe' if safe else 'banana']
        assert ('fall' in seen) == (not safe)
        assert d.beat is None


def test_peel_user_can_prevent_accident():
    d=StoryDirector();d.start('banana',safe=False)
    d.advance(.24)
    assert not d.rescue_peel()  # banana still in monkey's hand
    for _ in range(9):d.advance(.2)
    assert d.beat.prop == 'peel'
    assert d.rescue_peel()
    seen=[]
    while d.active:
        seen.append(d.beat.action)
        d.advance(.2)
    assert 'fall' not in seen


def test_story_cancel_cleans_up():
    d=StoryDirector();assert d.start('mirror')
    d.cancel()
    assert not d.active and d.beat is None
    assert d.start('blackboard')


def test_settings_roundtrip_and_unknown_fields(tmp_path):
    store=ConfigStore(tmp_path)
    a=Settings(mode='MONKEY',size=200,stories=False,skin='night',history=True)
    store.save(a)
    assert store.load() == a
    raw=json.loads(store.path.read_text())
    raw['hacker'] = 'ignore'
    raw['input_tracking'] = True
    store.path.write_text(json.dumps(raw))
    b=store.load()
    assert b.mode=='MONKEY' and not b.input_tracking


def test_settings_corrupted_is_safe(tmp_path):
    store=ConfigStore(tmp_path)
    store.path.write_text('not json')
    assert store.load().mode == 'QUIET'
    assert Settings(size=10000,mode='BAD',skin='BAD').validated().size==240


def test_history_privacy_off_and_opt_in(tmp_path):
    p=tmp_path/'events.json'
    h=History(p)
    h.add('banana')
    assert not p.exists()
    h.enabled=True;h.add('banana')
    assert p.exists()
    assert list(json.loads(p.read_text())[0]) == ['event','at']
    h.clear()
    assert not p.exists()


def test_gif_export_only_sprite_frames(tmp_path):
    from PIL import Image
    manifest = Path(__file__).resolve().parents[1]/'assets/monkey/manifest.json'
    output=tmp_path/'idle.gif'
    n=export_action_gif(manifest,'idle',output)
    assert n>=4
    with Image.open(output) as i:
        assert i.size == (160,160)
        assert i.n_frames>=4
    with pytest.raises(ValueError):export_action_gif(manifest,'../private',output)


def test_story_gif_excludes_external_capture(tmp_path):
    from PIL import Image
    manifest = Path(__file__).resolve().parents[1] / 'assets/monkey/manifest.json'
    out = tmp_path / 'banana.gif'
    n = export_story_gif(manifest, 'banana', out)
    assert n > 30
    with Image.open(out) as pic:
        assert pic.size == (420, 270)
        assert pic.n_frames >= 30
    with pytest.raises(ValueError):
        export_story_gif(manifest, '../../desktop', out)
