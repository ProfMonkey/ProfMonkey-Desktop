"""Headless tests for multi-pet soft collision physics."""
import pytest

from core.colony_physics import clamp_x, resolve_horizontal_collision
from core.config import ConfigStore, Settings
from core.physics import Body


def _collide(a, b, **overrides):
    values = dict(
        center_offset_a=0.0,
        center_offset_b=0.0,
        half_width_a=50.0,
        half_width_b=50.0,
        center_y_a=100.0,
        center_y_b=100.0,
        half_height_a=45.0,
        half_height_b=45.0,
    )
    values.update(overrides)
    return resolve_horizontal_collision(a, b, **values)


def test_pair_collision_separates_and_bounces_closing_bodies():
    a = Body(x=100, vx=80)
    b = Body(x=180, vx=-70)
    assert _collide(a, b)
    assert b.x-a.x >= 100
    assert a.vx < 0
    assert b.vx > 0


def test_pair_collision_ignores_nonoverlapping_or_vertical_separation():
    assert not _collide(Body(x=0), Body(x=140))
    assert not _collide(Body(x=0), Body(x=80), center_y_b=300)


def test_stationary_contact_gets_small_cartoon_bounce():
    a = Body(x=0)
    b = Body(x=70)
    assert _collide(a, b)
    assert a.vx < 0 < b.vx


def test_clamp_x_keeps_window_inside_work_area():
    bounds = (100.0, 0.0, 900.0, 700.0)
    assert clamp_x(-20, bounds, 200) == 100
    assert clamp_x(950, bounds, 200) == 700
    assert clamp_x(400, bounds, 200) == 400


def test_colony_behavior_and_collision_setting_round_trip(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(Settings(monkey_count=3, colony_behavior='follow', collisions_enabled=False))
    loaded = store.load()
    assert loaded.colony_behavior == 'follow'
    assert loaded.collisions_enabled is False


def test_invalid_colony_behavior_is_safely_normalized():
    settings = Settings(colony_behavior='delete_everything', collisions_enabled='no').validated()
    assert settings.colony_behavior == 'free'
    assert settings.collisions_enabled is True
