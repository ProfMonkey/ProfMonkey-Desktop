"""Multiple-monkey limits, non-overlapping spawn choices and persistence."""
import json
import pytest

from core.colony import MIN_MONKEYS, MAX_MONKEYS, clamp_count, spawn_position
from core.config import ConfigStore, Settings
from core.state import Brain, PetState


def test_monkey_count_limits():
    assert (MIN_MONKEYS, MAX_MONKEYS) == (1, 6)
    assert [clamp_count(n) for n in (-10, 0, 1, 2, 6, 20)] == [1, 1, 1, 2, 6, 6]
    with pytest.raises(ValueError):
        clamp_count(True)
    with pytest.raises(ValueError):
        clamp_count(2.8)


def test_unique_spawn_positions_on_normal_desktop():
    bounds = (0, 0, 1920, 1040)
    for n in range(1, 7):
        positions = [spawn_position(bounds, (278, 236), i, n) for i in range(n)]
        assert len(positions) == len(set(positions))
        assert all(0 <= x <= 1920-278 and y == 1040-236 for x, y in positions)
        assert positions[0] == (1920-278, 1040-236)


def test_spawn_position_respects_negative_monitor_and_tiny_screen():
    points = [spawn_position((-1900, 20, -1650, 210), (300, 230), i, 6)
              for i in range(6)]
    assert all(x == -1900 and y == 20 for x, y in points)
    with pytest.raises(ValueError):
        spawn_position((0, 0, 500, 500), (200, 200), 6, 6)


def test_count_is_saved_and_normalized(tmp_path):
    store = ConfigStore(tmp_path)
    assert store.load().monkey_count == 1
    settings = Settings(monkey_count=5).validated()
    store.save(settings)
    assert store.load().monkey_count == 5
    assert json.loads(store.path.read_text(encoding='utf-8'))['monkey_count'] == 5
    store.path.write_text('{"monkey_count": 999}', encoding='utf-8')
    assert store.load().monkey_count == 6
    store.path.write_text('{"monkey_count": 0}', encoding='utf-8')
    assert store.load().monkey_count == 1


def test_individual_brains_and_states_do_not_share_random_streams():
    a, b = PetState(), PetState()
    a.tap()
    assert b.mood == 15
    brain1, brain2 = Brain(seed=1), Brain(seed=2)
    results1, results2 = [], []
    for _ in range(25):
        brain1.reset(); brain2.reset()
        results1.append(brain1.next(a, 1))
        results2.append(brain2.next(b, 1))
    assert results1 != results2
