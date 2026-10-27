"""Pure Python determinism/transition tests (Qt is NOT required)."""
import json
from pathlib import Path

import pytest

from core.animation import AnimationPlayer, AnimationSpec, DemoTimeline, load_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/monkey/manifest.json"


def test_manifest_resolves_all_delivered_animation_frames():
    specs = load_manifest(MANIFEST)
    assert {'idle', 'blink', 'walk', 'turn', 'sleep', 'wake', 'fall', 'get_up'} <= set(specs)
    assert sum(len(spec.frames) for spec in specs.values()) >= 40
    from core.character_art import CHARACTERS, pose_svg
    # v0.20 deliberately keeps the old manifest's sequencing metadata,
    # but paints every frame from bundled editable SVG instead of missing
    # legacy binary frames. All six must support every advertised action.
    for spec in specs.values():
        for persona in CHARACTERS:
            for i, _frame_name in enumerate(spec.frames):
                svg = pose_svg(MANIFEST.parent, persona, spec.name,
                               i, len(spec.frames))
                assert b'viewBox="0 0 256 256"' in svg
        assert spec.anchor == (0.5, 0.96)


def test_walk_advances_and_loops_with_irregular_dt():
    p = AnimationPlayer(load_manifest(MANIFEST))
    assert p.request('walk')
    assert p.frame_index == 0
    p.advance(1 / 9)
    assert p.frame_index == 1
    p.advance(7 / 9)
    assert p.action == 'walk' and p.frame_index == 0
    p.advance(8 / 9 * 10 + 2 / 9)
    assert p.frame_index == 2


def test_non_loop_action_returns_to_idle():
    p = AnimationPlayer(load_manifest(MANIFEST))
    assert p.request('blink', force=True)
    assert p.action == 'blink'
    p.advance(0.34)
    assert p.action == 'idle'
    assert p.frame_index == 0


def test_fall_has_non_skippable_recovery_chain():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.request('fall', force=True)
    assert not p.request('walk')
    p.advance(0.61)
    assert p.action == 'get_up'
    assert not p.request('idle')
    p.advance(6 / 9 + 0.05)
    assert p.action == 'idle'
    assert p.frame_index == 0


def test_force_can_interrupt_any_action_for_explicit_user_control():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.request('fall', force=True)
    assert p.request('sleep', force=True)
    assert p.action == 'sleep'


def test_priority_blocks_lower_action_and_allows_equal_or_higher():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.request('sleep', force=True)
    assert not p.request('walk')
    assert p.request('wake', force=True)
    assert not p.request('blink')  # awake transition locks while playing


def test_unknown_action_safe_fallback():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.request('does-not-exist', force=True)
    assert p.action == 'idle'
    assert p.frame_path.endswith('.png')


def test_pausing_freezes_animation():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.request('walk')
    p.paused = True
    assert p.advance(2) is False
    assert p.frame_index == 0
    p.paused = False
    assert p.advance(1 / 9)
    assert p.frame_index == 1


def test_facing_flip_does_not_change_timing_or_frame():
    p = AnimationPlayer(load_manifest(MANIFEST))
    p.face(-1)
    assert p.facing == -1
    p.advance(.25)
    assert p.facing == -1
    with pytest.raises(ValueError):
        p.face(0)


def test_invalid_deltas_rejected():
    p = AnimationPlayer(load_manifest(MANIFEST))
    for dt in [-1, float('nan'), float('inf')]:
        with pytest.raises(ValueError):
            p.advance(dt)


def test_demo_sequence_replays_without_randomness():
    t = DemoTimeline((('idle', .5), ('blink', .2), ('walk', .4)))
    assert t.advance(.49) is None
    assert t.advance(.01) == 'blink'
    assert t.advance(.2) == 'walk'
    assert t.advance(.4) == 'idle'
    assert t.step_index == 0
    t.reset()
    assert t.step_index == 0 and t.elapsed == 0


def test_manifest_rejects_path_traversal(tmp_path):
    raw = json.loads(MANIFEST.read_text(encoding='utf-8'))
    raw['states']['walk']['frames'][0] = '../../secrets.png'
    p = tmp_path / 'malicious.json'
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='Unsafe'):
        load_manifest(p)


def test_manifest_rejects_differing_anchors(tmp_path):
    raw = json.loads(MANIFEST.read_text(encoding='utf-8'))
    raw['states']['walk']['anchor_normalized'] = [0.1, 0.95]
    p = tmp_path / 'invalid.json'
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='anchor'):
        load_manifest(p)


def test_animation_specs_require_positive_frame_rate():
    with pytest.raises(ValueError):
        AnimationSpec('bad', ('any.png',), 0, True, 0, True)
