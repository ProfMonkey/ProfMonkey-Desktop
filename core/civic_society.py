"""v0.19 opt-in fictional civil society: reproducible, read-only consequences.

No extra journal files, background timers, OS monitoring, real economies or
unprompted notifications. Society is derived from *existing* city stories,
history choices, laws, buildings, profiles and monkey-to-monkey relationships.
A new choice can change roles, factions, local animation weights and dialogue
at the next in-game refresh. Merely reading this module never writes a save.
"""
from __future__ import annotations

from dataclasses import dataclass
from core.civilization import BUILDINGS
from core.city_evolution import LEGACY_EVENTS, evolution_era
from core.profiles import clean_profiles

ROLE_NAMES = {
    'banana_vault': '🍌 仓库管理员',
    'galaxy_scope': '🔭 星际观测员',
    'public_square': '🎉 广场策划师',
    'monkey_academy': '🧪 联合实验员',
}
PREFERRED_BUILDINGS = {
    'scholar': ('galaxy_scope', 'monkey_academy', 'banana_vault', 'public_square'),
    'trickster': ('public_square', 'banana_vault', 'galaxy_scope', 'monkey_academy'),
    'sleepy': ('banana_vault', 'public_square', 'galaxy_scope', 'monkey_academy'),
    'inventor': ('monkey_academy', 'galaxy_scope', 'banana_vault', 'public_square'),
    'captain': ('banana_vault', 'public_square', 'monkey_academy', 'galaxy_scope'),
    'shy': ('galaxy_scope', 'monkey_academy', 'public_square', 'banana_vault'),
}
PERSONALITY_LEAN = {
    'scholar': 2, 'trickster': -2, 'sleepy': 0,
    'inventor': -2, 'captain': 1, 'shy': 2,
}
FACTIONS = {'community': '🤝 共治派', 'pioneer': '⚡ 开拓派', 'independent': '🌿 独行派'}


@dataclass(frozen=True)
class CivicMember:
    index: int
    name: str
    personality: str
    building: str | None
    role: str
    faction: str
    preference: int


@dataclass(frozen=True)
class CivicSnapshot:
    era: str
    cooperation: int
    innovation: int
    tension: int
    members: tuple[CivicMember, ...]
    headlines: tuple[str, ...]
    # In-game meeting vs banana duel; only used if separate group auto-mode is on.
    meeting_probability: float


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _relation(relations: object, a: int, b: int) -> dict:
    if relations is None:
        return {}
    getter = getattr(relations, 'get', None)
    if not callable(getter):
        return {}
    try:
        value = getter(a, b)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, IndexError):
        return {}


def _law(laws: object, key: str) -> bool:
    return bool(laws is not None and callable(getattr(laws, 'active', None))
                and laws.active(key))


def city_society(journal: object, laws=None, relationships=None,
                 profiles=None, count: int = 6) -> CivicSnapshot:
    """Snapshot the six fictional monkeys; use no randomness or wall-clock time.

    Never accepts arbitrary historical or real-world events. No balance changes
    occur here; it is a *consequence viewer*, not an automatic resource miner.
    """
    if type(count) is not int or not 1 <= count <= 6:
        raise ValueError('monkey count must be 1 through 6')
    people = clean_profiles(profiles)
    owned = journal.buildings
    if not isinstance(owned, frozenset) or any(k not in BUILDINGS for k in owned):
        raise ValueError('invalid city buildings')
    history = journal.legacy_events
    cases = journal.city_cases
    community = sum(row.get('route') == 'community' for row in history)
    pioneer = sum(row.get('route') == 'elite' for row in history)
    reconciled = sum(row.get('ending') == 'reconciled' for row in cases.values())
    unresolved = sum(row.get('ending') == 'chaos' for row in cases.values())
    # Starting values are intentionally modest; actual events dominate climate.
    cooperation = 20 + 9 * community - 4 * pioneer + 5 * reconciled - 6 * unresolved
    innovation = 18 + 11 * pioneer + 3 * community
    tension = 12 + 10 * pioneer + 7 * unresolved - 6 * community - 4 * reconciled
    if _law(laws, 'banana_rules'):
        cooperation += 8
        tension -= 5
    if _law(laws, 'quiet_hours'):
        tension -= 7
    if _law(laws, 'rocket_license'):
        innovation += 8

    # Existing relationship history matters, without recording any new visit.
    bonds, rivals, trusts = [], [], []
    for i in range(count):
        for j in range(i+1, count):
            relation = _relation(relationships, i, j)
            for values, key in ((bonds, 'bond'), (rivals, 'rivalry'), (trusts, 'trust')):
                raw = relation.get(key, 0)
                values.append(raw if type(raw) is int else 0)
    if bonds:
        cooperation += sum(bonds) // (len(bonds)*5)
        cooperation += sum(trusts) // (len(trusts)*5)
        tension += sum(rivals) // (len(rivals)*4)
    cooperation, innovation, tension = map(_clamp, (cooperation, innovation, tension))
    lean = 2 * (community - pioneer) + reconciled - unresolved
    members = []
    for index in range(count):
        personality = people[index]['personality']
        role_building = next((key for key in PREFERRED_BUILDINGS[personality]
                              if key in owned), None)
        preference = PERSONALITY_LEAN[personality] + lean
        # Current friendships and rivalries create local differences within
        # the same citywide political climate (fictional, never real profiling).
        relation_bond = 0
        for partner in range(count):
            if partner == index:
                continue
            pair = _relation(relationships, index, partner)
            relation_bond += (pair.get('trust', 0) if type(pair.get('trust')) is int else 0)
            relation_bond -= (pair.get('rivalry', 0) if type(pair.get('rivalry')) is int else 0)
        if count > 1:
            preference += max(-2, min(2, relation_bond // (15*(count-1))))
        faction = ('community' if preference >= 2 else
                   'pioneer' if preference <= -2 else 'independent')
        members.append(CivicMember(
            index, people[index]['name'], personality, role_building,
            ROLE_NAMES[role_building] if role_building else '🌱 自由探险者',
            faction, preference))
    _, era = evolution_era(journal)
    headlines = [
        f'📍 {era} · 建筑 {len(owned)}/4 · 历史抉择 {len(history)}/{len(LEGACY_EVENTS)}',
        f'🤝 合作 {cooperation}/100 · 🔬 创新 {innovation}/100 · ⚡ 分歧 {tension}/100',
    ]
    if not owned:
        headlines.append('猴山还没有公共建筑。现在只有自由探险者。')
    for key, title in (
        ('granary', '香蕉仓库开始实施新的钥匙制度。'),
        ('star_chart', '研究组正在讨论星图成果的归属。'),
        ('festival_custom', '广场出现了持续性的节庆传统。'),
        ('safety_code', '实验室正在依照历史选择运作。'),
        ('constitution', '猴山已写下自己的共同宪章。'),
    ):
        chosen = next((e for e in history if e.get('event') == key), None)
        if chosen:
            path = '合作' if chosen['route'] == 'community' else '突破'
            headlines.append(f'• {title}（{path}路线）')
    if len(headlines) == 2:
        headlines.append('先完成城市原案和文明演化，城市社会才会逐渐形成传统。')
    probability = max(.12, min(.88, .50 + (cooperation-tension)/180))
    return CivicSnapshot(era, cooperation, innovation, tension, tuple(members),
                         tuple(headlines[:8]), round(probability, 3))


def civic_action_bias(member: CivicMember, snapshot: CivicSnapshot) -> tuple[int, ...]:
    """Animation weights (idle, walk, blink, sleep, turn, run).

    They only bias already-supported sprite actions; no fake animations, GUI
    side effects, new resource generation, or user input inspection.
    """
    if not isinstance(member, CivicMember) or not isinstance(snapshot, CivicSnapshot):
        raise ValueError('invalid society snapshot')
    if member.building is None:
        return (0, 0, 0, 0, 0, 0)
    weights = {
        'banana_vault': (2, 9, 0, 0, 5, 2),
        'galaxy_scope': (9, 0, 13, 0, 0, 0),
        'public_square': (0, 12, 2, 0, 5, 6),
        'monkey_academy': (8, 0, 13, 0, 4, 0),
    }[member.building]
    extra = (4, 0, 3, 0, 0, 0) if member.faction == 'community' else (
        (0, 6, 0, 0, 3, 5) if member.faction == 'pioneer'
        else (3, 0, 0, 3, 0, 0))
    if snapshot.tension >= 55:
        extra = tuple(extra[i] + (3 if i == 4 else 0) for i in range(6))
    return tuple(weights[i] + extra[i] for i in range(6))


def civic_encounter(a: object, b: object, relations: dict,
                    snapshot: CivicSnapshot):
    """An actual two-beat local interaction reflecting history and factions.

    Import at call time so older encounter paths remain independent. A simple
    decorative bulletin is never substituted for this functional interaction.
    """
    from core.encounters import Encounter
    if not isinstance(snapshot, CivicSnapshot):
        return None
    if not (0 <= a.index < len(snapshot.members) and
            0 <= b.index < len(snapshot.members) and a.index != b.index):
        return None
    left, right = snapshot.members[a.index], snapshot.members[b.index]
    if left.building is None and right.building is None:
        return None
    rivalry = relations.get('rivalry', 0)
    trust = relations.get('trust', 0)
    if type(rivalry) is not int: rivalry = 0
    if type(trust) is not int: trust = 0
    clash = ({left.faction, right.faction} == {'community', 'pioneer'}
             and snapshot.tension >= 25 and rivalry >= 15)
    if clash:
        return Encounter(a.index, b.index, 'civic_dispute',
                         'angry', 'angry',
                         f'我们{FACTIONS[left.faction]}主张先谈妥分工！',
                         f'可是{FACTIONS[right.faction]}想现在就做实验！',
                         a.personality, b.personality,
                         outcome_first=('blink', '先把这次分歧记录在议会档案里。'),
                         outcome_second=('idle', '下次见面再谈，也许会找到共识。'))
    if (left.building == 'monkey_academy' or
            right.building == 'monkey_academy') and snapshot.innovation >= 30:
        return Encounter(a.index, b.index, 'civic_research',
                         'blink', 'wake',
                         f'{left.role}：先检查一下历史研究记录。',
                         f'{right.role}：这次我们把结果写进公开档案。',
                         a.personality, b.personality,
                         outcome_first=('blink', '旧实验事故提醒我们要先验证。'),
                         outcome_second=('wake', '这份数据将成为下一次研究的线索！'))
    if left.building == 'public_square' or right.building == 'public_square':
        return Encounter(a.index, b.index, 'civic_festival',
                         'walk', 'wake',
                         f'{left.role}：今天的广场需要大家帮忙。',
                         f'{right.role}：我会按新传统参加！',
                         a.personality, b.personality,
                         outcome_first=('walk', '把旧庆典留下的舞台收拾好！'),
                         outcome_second=('blink', '明年我们还能继续在这里演出。'))
    if trust >= 15 or snapshot.cooperation >= 35:
        return Encounter(a.index, b.index, 'civic_cooperate',
                         'wake', 'blink',
                         f'{left.role}申请协助你的工作。',
                         f'{right.role}已收到，我们轮流值班！',
                         a.personality, b.personality,
                         outcome_first=('wake', '合作完成，今天的值班记录写好了。'),
                         outcome_second=('blink', '下回我们还可以换个岗位试试。'))
    return Encounter(a.index, b.index, 'civic_patrol',
                     'walk', 'blink',
                     f'{left.role}正在查看最近的猴山日报。',
                     f'{right.role}：还得看看旧案件怎么处理的。',
                     a.personality, b.personality,
                     outcome_first=('blink', '旧档案都核对完了。'),
                     outcome_second=('idle', '继续巡查，保持猴山整洁！'))


def society_report(snapshot: CivicSnapshot) -> str:
    """Readable preview; all values follow from existing local in-game data."""
    rows = ['🏛️ 猴山自主社会 · 当前沙盒快照', *snapshot.headlines,
            '', '🐒 成员职责 / 意见阵营']
    rows += [f'#{m.index+1} {m.name} · {m.role} · {FACTIONS[m.faction]}'
             for m in snapshot.members]
    rows += ['', '💬 模拟行为说明：建筑岗位会影响散步、观察、思考等动作；'
             '已选择不同路线的猴子在碰面时可能合作或争论。',
             '🔕 该面板只读取本地虚构存档。关闭自主社会开关后，'
             '不会修改日常动作权重或旧版偶遇。']
    return '\n'.join(rows)
