"""v0.18 offline regression: real journal, laws, choices and save rollback."""
from dataclasses import replace
import json
import pytest

from core.civilization import BUILDINGS
from core.city_life import prepare_city_case
from core.city_evolution import (LEGACY_EVENTS, clean_legacy, evolution_era,
                                 evolution_report, legacy_status, prepare_evolution)
from core.expeditions import ExpeditionJournal, newspaper


class Laws:
    def __init__(self, *active):
        self.current = set(active)

    def active(self, key):
        return key in self.current


class Bonds:
    def __init__(self, bond=0, trust=0):
        self.bond = bond
        self.trust = trust

    def get(self, first, second):
        return {'bond': self.bond, 'trust': self.trust}


def make_city(tmp_path):
    journal = ExpeditionJournal(tmp_path / 'expeditions.json')
    journal.resources.update(bananas=200, science=200, reputation=200)
    for building in BUILDINGS:
        assert journal.construct(building)
    return journal


def close_case(journal, case, route='careful'):
    for _ in range(3):
        plan = prepare_city_case(case, journal.city_cases[case], 0, 1, route)
        assert journal.record_city_chapter(plan)


def test_old_saves_and_empty_city_never_unlock_free_sequels(tmp_path):
    journal = ExpeditionJournal(tmp_path / 'old.json')
    assert journal.legacy_events == []
    assert evolution_era(journal)[0] == 0
    for event in LEGACY_EVENTS:
        assert not legacy_status(event, journal)[0]


def test_each_original_case_unlocks_its_own_one_time_sequel(tmp_path):
    journal = make_city(tmp_path)
    for event, spec in list(LEGACY_EVENTS.items())[:4]:
        assert not legacy_status(event, journal)[0]
        close_case(journal, spec.source)
        assert legacy_status(event, journal)[0]
        plan = prepare_evolution(event, 'community', journal)
        assert len(plan.scenes) == 3
        before = journal.resources.copy()
        assert journal.record_evolution(plan)
        assert len(journal.legacy_events) <= 4
        for key, delta in zip(('bananas', 'science', 'reputation'), plan.resource_delta):
            assert journal.resources[key] == before[key] + delta
        assert not journal.record_evolution(plan)
    fresh = ExpeditionJournal(journal.path)
    assert fresh.legacy_events == journal.legacy_events
    assert evolution_era(fresh)[0] == 3
    assert '文明演化' in newspaper(fresh)


def test_old_ending_changes_later_outcome(tmp_path):
    journal = make_city(tmp_path)
    close_case(journal, 'banana_vault', route='bold')
    cautious = prepare_evolution('granary', 'community', journal)
    secret = prepare_evolution('granary', 'elite', journal)
    assert cautious.resource_delta == (-2, 0, 3)
    assert secret.resource_delta == (2, 0, -3)
    assert '争议至今' in secret.scenes[0]


def test_constitution_checks_cases_law_routes_and_pair_bond_at_commit(tmp_path):
    journal = make_city(tmp_path)
    for key in ('banana_vault', 'galaxy_scope', 'public_square'):
        close_case(journal, key)
    for event, route in (('granary', 'community'), ('star_chart', 'elite')):
        assert journal.record_evolution(prepare_evolution(event, route, journal))
    laws = Laws('banana_rules')
    bonds = Bonds(10, 12)
    assert legacy_status('constitution', journal, laws, bonds)[0]
    plan = prepare_evolution('constitution', 'community', journal, laws, bonds)
    laws.current.clear()
    before = journal.resources.copy()
    assert not journal.record_evolution(plan, laws, bonds)
    assert journal.resources == before
    laws.current.add('banana_rules')
    bonds.trust = 0
    assert not journal.record_evolution(plan, laws, bonds)
    bonds.trust = 12
    assert journal.record_evolution(plan, laws, bonds)
    assert evolution_era(journal)[0] == 4
    assert not journal.record_evolution(plan, laws, bonds)


def test_forged_rewards_cast_and_route_cannot_grant_resources(tmp_path):
    journal = make_city(tmp_path)
    close_case(journal, 'banana_vault')
    valid = prepare_evolution('granary', 'elite', journal)
    start = journal.resources.copy()
    for forged in (replace(valid, resource_delta=(999, 999, 999)),
                   replace(valid, first=True),
                   replace(valid, route='unexpected'),
                   replace(valid, scenes=('done',) * 3)):
        assert not journal.record_evolution(forged)
    assert journal.resources == start
    assert not journal.legacy_events


def test_no_bankruptcy_and_disk_failure_roll_back(tmp_path, monkeypatch):
    journal = make_city(tmp_path)
    close_case(journal, 'banana_vault')
    plan = prepare_evolution('granary', 'community', journal)
    journal.resources['bananas'] = 0
    assert not journal.record_evolution(plan)
    journal.resources['bananas'] = 20
    balance = journal.resources.copy()
    history = journal.legacy_events.copy()
    def disk_full():
        raise OSError('disk full')
    monkeypatch.setattr(journal, '_save', disk_full)
    assert not journal.record_evolution(plan)
    assert journal.resources == balance
    assert journal.legacy_events == history


def test_corrupted_v018_save_does_not_unlock_unknown_history(tmp_path):
    journal = make_city(tmp_path)
    close_case(journal, 'banana_vault')
    payload = json.loads(journal.path.read_text(encoding='utf-8'))
    payload['legacy_events'] = [
        {'event': 'granary', 'route': 'community'},
        {'event': 'granary', 'route': 'elite'},
        {'event': 'star_chart', 'route': 'community'},
        {'event': True, 'route': 'elite'},
        {'event': 'constitution', 'route': 'elite'}]
    journal.path.write_text(json.dumps(payload), encoding='utf-8')
    loaded = ExpeditionJournal(journal.path)
    assert loaded.legacy_events == [{'event': 'granary', 'route': 'community'}]
    assert not legacy_status('granary', loaded)[0]


def test_clear_legacy_history_preserves_other_files(tmp_path):
    journal = make_city(tmp_path)
    close_case(journal, 'banana_vault')
    assert journal.record_evolution(prepare_evolution('granary', 'elite', journal))
    other = tmp_path / 'relationships.json'
    other.write_text('preserve', encoding='utf-8')
    journal.clear()
    assert journal.legacy_events == []
    assert not journal.path.exists()
    assert other.read_text(encoding='utf-8') == 'preserve'


def test_report_is_read_only_and_labels_locked_future(tmp_path):
    journal = make_city(tmp_path)
    text = evolution_report(journal)
    assert '文明纪元' in text
    assert '先建好对应建筑' in text
    assert not journal.legacy_events
