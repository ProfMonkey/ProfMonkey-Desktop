"""Persistent fictional monkey city: four constructible buildings and safe bonuses.

The city itself has no filesystem or Qt dependency. Currency and owned
buildings are committed together in the *same* ExpeditionJournal JSON file,
avoiding inconsistent two-file transactions. Only in-game resources are used.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Building:
    title: str
    description: str
    cost: tuple[int, int, int]  # bananas, science, fictional reputation
    requires: tuple[str, ...] = ()
    mission: str | None = None
    prop: str = ''


BUILDINGS: dict[str, Building] = {
    'banana_vault': Building(
        '🍌 香蕉研究仓库', '香蕉侦察队：协作+1；有收获时额外获得1根香蕉。',
        (12, 0, 0), mission='banana_scout', prop='banana_vault'),
    'galaxy_scope': Building(
        '🔭 银河猴山望远镜', '陨石研究所：协作+1；有收获时科研点额外+1。',
        (0, 12, 0), mission='meteor_lab', prop='galaxy_scope'),
    'public_square': Building(
        '🏛️ 猴山公共广场', '猴山营造队：协作+1；有收获时声望额外+1。',
        (0, 0, 12), mission='village_repair', prop='public_square'),
    'monkey_academy': Building(
        '🌌 银河猴山联合实验室', '所有小队协作+1；需先完成三座基础建筑。',
        (20, 20, 20),
        requires=('banana_vault', 'galaxy_scope', 'public_square'),
        prop='monkey_academy'),
}
RESOURCE_LABELS = ('🍌 香蕉', '🔬 科研点', '⭐ 猴山声望')


def sanitize_city(raw: object) -> frozenset[str]:
    """Safely load city ownership from untrusted/old local saves."""
    if not isinstance(raw, list):
        return frozenset()
    owned = {name for name in raw if type(name) is str and name in BUILDINGS}
    # Advanced projects are never valid without their prerequisite buildings.
    return frozenset(
        name for name in owned
        if all(dep in owned for dep in BUILDINGS[name].requires))


def construction_status(building: str, resources: dict[str, int],
                        owned: frozenset[str]) -> tuple[bool, str]:
    """Return eligibility without modifying balances, ownership, or disk."""
    if type(building) is not str or building not in BUILDINGS:
        return False, '无效的猴山建筑。'
    if building in owned:
        return False, '这座建筑已经建成，无需重复扣除资源。'
    spec = BUILDINGS[building]
    missing = [BUILDINGS[key].title for key in spec.requires if key not in owned]
    if missing:
        return False, '请先建造：' + '、'.join(missing)
    keys = ('bananas', 'science', 'reputation')
    cost_missing = []
    for key, label, amount in zip(keys, RESOURCE_LABELS, spec.cost):
        available = resources.get(key, 0)
        if type(available) is not int or available < amount:
            cost_missing.append(f'{label}还需 {amount - max(0, available) if type(available) is int else amount}')
    if cost_missing:
        return False, '资源不足：' + '；'.join(cost_missing)
    return True, '已满足建造条件，可以建造。'


def mission_city_bonus(mission: str, owned: frozenset[str],
                       outcome: str | None = None) -> tuple[int, tuple[int, int, int]]:
    """Deterministic score + bonus resources from an expedition start snapshot."""
    score_bonus = 0
    resource_bonus = [0, 0, 0]
    mission_keys = ('banana_scout', 'meteor_lab', 'village_repair')
    if mission not in mission_keys:
        return 0, (0, 0, 0)
    for name, building in BUILDINGS.items():
        if name not in owned:
            continue
        if name == 'monkey_academy':
            score_bonus += 1
        elif building.mission == mission:
            score_bonus += 1
            if outcome in ('success', 'mixed'):
                resource_bonus[mission_keys.index(mission)] += 1
    return score_bonus, tuple(resource_bonus)


def city_tier(owned: frozenset[str]) -> tuple[int, str]:
    """Progress reflects actual construction, not merely available cash."""
    if 'monkey_academy' in owned:
        return 4, '🌌 银河猴山文明'
    count = sum(name in owned for name in BUILDINGS if name != 'monkey_academy')
    return count, ('🌱 初生猴山', '🏕️ 猴山聚落', '🏘️ 猴山小镇',
                   '🏙️ 猴山城邦')[count]


def city_report(owned: frozenset[str], resources: dict[str, int],
                cases: dict[str, dict] | None = None) -> str:
    level, title = city_tier(owned)
    lines = [f'🏗️ 文明阶段 {level}/4 · {title}',
             f'🏦 可用资源：🍌 {resources["bananas"]} | '
             f'🔬 {resources["science"]} | ⭐ {resources["reputation"]}']
    for key, building in BUILDINGS.items():
        flag = '✅ 已建成' if key in owned else '🔒 待建设'
        eligible, detail = construction_status(key, resources, owned)
        lines.append(f'{flag} {building.title} · ' +
                     ('资源足够，点击建造' if eligible else
                      ('已在猴山落成' if key in owned else detail)))
    if isinstance(cases, dict):
        lines.append('🗞️ 城市故事进度：')
        for key in BUILDINGS:
            if key not in owned:
                continue
            row = cases.get(key)
            stage = row.get('chapter') if isinstance(row, dict) else 0
            stage = stage if type(stage) is int and 0 <= stage <= 3 else 0
            suffix = ('✅ 结案' if stage == 3 else f'第{stage+1}章待演出')
            lines.append(f'• {BUILDINGS[key].title} · {suffix}')
    return '\n'.join(lines)
