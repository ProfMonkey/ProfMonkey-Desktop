"""v0.18: deterministic, opt-in sequels driven by v0.17 city history.

All resources are fictional. Nothing runs in the background. The four city
cases, active in-game monkey laws and recorded relationship scores unlock
one-time decisions; events are never generated from the user's actual desktop.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class LegacyEvent:
    title: str
    source: str | None
    intro: str
    choices: tuple[str, str]
    deltas: tuple[tuple[int, int, int], tuple[int, int, int]]
    scenes: tuple[str, str, str]


LEGACY_EVENTS = {
    'granary': LegacyEvent(
        '🍌 第二次仓库会议', 'banana_vault',
        '香蕉失窃案结案后，仓库决定重新分配钥匙。',
        ('共管钥匙，让大家轮流核查', '秘密追踪，强化仓库警戒'),
        ((-2, 0, 3), (2, 0, -2)),
        ('失窃案的旧收据重新摆上桌面。', '一张新钥匙登记表引起激烈争论。',
         '一套新制度将成为猴山未来的日常。')),
    'star_chart': LegacyEvent(
        '🔭 星图的第二个坐标', 'galaxy_scope',
        '第一张星图发布后，第二次信号居然来自猴山内部。',
        ('公开原始观测，让所有猴子复核', '保留发现，秘密研发探测器'),
        ((0, -1, 3), (0, 4, -2)),
        ('望远镜重新捕捉到曾经的奇异脉冲。', '旧日志上的数字指向广场钟楼。',
         '猴山必须决定科学发现属于谁。')),
    'festival_custom': LegacyEvent(
        '🎉 庆典后的第一条传统', 'public_square',
        '第一届庆典结束了，但广场上仍留着未拆的舞台。',
        ('每个猴子都能申请登台', '成立精英表演队，打造王牌节目'),
        ((-1, 0, 4), (0, 0, 2)),
        ('一位从未表演过的猴子走进广场。', '观众在普通节目与超级表演之间投票。',
         '新的节日习俗从今天开始延续。')),
    'safety_code': LegacyEvent(
        '🧪 事故后的安全复盘', 'monkey_academy',
        '实验室恢复运转，曾经失控的仪器却再次报警。',
        ('建立透明审计和双猴复核', '允许高风险突破实验'),
        ((0, -2, 4), (0, 5, -3)),
        ('封存的紫色实验记录再次被翻开。', '发明猴和学究猴对同一组数据给出不同解释。',
         '新标准会影响此后所有科研讨论。')),
    'constitution': LegacyEvent(
        '🏛️ 猴山共同宪章', None,
        '跨越案件、科研、节庆与自治后，猴山终于能订立自己的共同承诺。',
        ('建立公开议事与协商机制', '交给少数精英快速决定'),
        ((-2, -2, 7), (3, 2, -3)),
        ('猴山广场挂起历次事件的案卷。', '大家朗读已通过的法令，讨论谁可以参与。',
         '猴山文明写下第一份自己的宪章。')),
}
ROUTES = ('community', 'elite')
RESOURCE_KEYS = ('bananas', 'science', 'reputation')
MAX_LEGACY = len(LEGACY_EVENTS)


@dataclass(frozen=True)
class EvolutionPlan:
    event_id: str
    route: str
    first: int
    second: int
    source_ending: str
    resource_delta: tuple[int, int, int]
    scenes: tuple[str, str, str]


def clean_legacy(raw: object, city_cases: dict, buildings: frozenset[str]) -> list[dict[str, str]]:
    """Old saves work; unknown, duplicate or unearned history is ignored.

    A saved branch is a fact about a past choice, so repealing a law later
    cannot erase that fact. It cannot produce a second reward on reload.
    """
    if not isinstance(raw, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in raw[:MAX_LEGACY]:
        if not isinstance(entry, dict):
            continue
        event, route = entry.get('event'), entry.get('route')
        if (type(event) is not str or event not in LEGACY_EVENTS or
                event in seen or type(route) is not str or route not in ROUTES):
            continue
        spec = LEGACY_EVENTS[event]
        if spec.source is not None:
            row = city_cases.get(spec.source, {})
            if (spec.source not in buildings or not isinstance(row, dict) or
                    row.get('chapter') != 3):
                continue
        elif not (len([row for row in city_cases.values()
                       if isinstance(row, dict) and row.get('chapter') == 3]) >= 3
                  and len([e for e in result if e['event'] != 'constitution']) >= 2):
            continue
        seen.add(event)
        result.append({'event': event, 'route': route})
    return result


def _law_active(laws: object, name: str) -> bool:
    return bool(laws and callable(getattr(laws, 'active', None)) and laws.active(name))


def _pair_values(relationships: object, first: int, second: int) -> dict:
    if relationships is None:
        return {}
    if callable(getattr(relationships, 'get', None)):
        try:
            result = relationships.get(first, second)
            return result if isinstance(result, dict) else {}
        except (ValueError, TypeError):
            pass
    return {}


def legacy_status(event_id: str, journal: object, laws=None, relationships=None,
                  first: int = 0, second: int = 1) -> tuple[bool, str]:
    """Compute eligibility from saved case outcomes, laws, bonds, and history."""
    if type(event_id) is not str or event_id not in LEGACY_EVENTS:
        return False, '未知后续事件。'
    if any(row.get('event') == event_id for row in journal.legacy_events):
        return False, '已经写入猴山史册，无法反复结算。'
    source = LEGACY_EVENTS[event_id].source
    if source is not None:
        row = journal.city_cases.get(source, {})
        if source not in journal.buildings or row.get('chapter') != 3:
            return False, '先建好对应建筑并完成原案全部三章。'
    else:
        settled = sum(row.get('chapter') == 3 for row in journal.city_cases.values())
        constructive = sum(row.get('route') == 'community' for row in journal.legacy_events)
        law = any(_law_active(laws, key) for key in ('banana_rules', 'quiet_hours', 'rocket_license'))
        if settled < 3 or len(journal.legacy_events) < 2 or constructive < 1:
            return False, '需要至少3件结案、2次历史后续事件及1次公开合作选择。'
        if not law:
            return False, '还需要一项猴山议会已经通过且仍有效的法令。'
        if (type(first) is not int or type(second) is not int or first == second or
                not 0 <= first < 6 or not 0 <= second < 6):
            return False, '请选择两只不同的猴子参与宪章。'
        pair = _pair_values(relationships, first, second)
        if pair.get('trust', 0) < 8 or pair.get('bond', 0) < 6:
            return False, '两位起草猴子还需要更多信任（信任≥8、好感≥6）。'
    return True, '条件满足，可以开启一次新的历史抉择。'


def evolution_delta(event_id: str, route: str, source_ending: str) -> tuple[int, int, int]:
    """A reconciled old case increases the next chapter's public legitimacy."""
    if (type(event_id) is not str or event_id not in LEGACY_EVENTS or
            type(route) is not str or route not in ROUTES or
            type(source_ending) is not str or source_ending not in ('', 'reconciled', 'chaos')):
        raise ValueError('invalid city evolution plan')
    idx = ROUTES.index(route)
    base = LEGACY_EVENTS[event_id].deltas[idx]
    return base[:2] + (base[2] + (1 if source_ending == 'reconciled' and route == 'community' else
                                 -1 if source_ending == 'chaos' and route == 'elite' else 0),)


def prepare_evolution(event_id: str, route: str, journal: object, laws=None,
                      relationships=None, first: int = 0, second: int = 1) -> EvolutionPlan:
    if (type(first) is not int or type(second) is not int or
            first == second or not 0 <= first < 6 or not 0 <= second < 6 or
            type(route) is not str or route not in ROUTES):
        raise ValueError('invalid cast or route')
    valid, reason = legacy_status(event_id, journal, laws, relationships, first, second)
    if not valid:
        raise ValueError(reason)
    event = LEGACY_EVENTS[event_id]
    ending = journal.city_cases[event.source]['ending'] if event.source else ''
    history = ('旧案已经达成和解。' if ending == 'reconciled' else
               '旧案的争议至今没有消失。' if ending == 'chaos' else
               '先前的决定已经改变了猴山。')
    line = event.choices[ROUTES.index(route)]
    scenes = (event.scenes[0] + history, event.scenes[1] + '决定：' + line + '。',
              event.scenes[2] + ('猴际关系更亲密。' if route == 'community'
                                else '新的分歧正在酝酿。'))
    return EvolutionPlan(event_id, route, first, second, ending,
                         evolution_delta(event_id, route, ending), scenes)


def evolution_era(journal: object) -> tuple[int, str]:
    """Civic era is derived from actual milestones, never elapsed wall time."""
    if any(row.get('event') == 'constitution' for row in journal.legacy_events):
        return 4, '🏛️ 猴山共治时代'
    if len(journal.legacy_events) >= 2:
        return 3, '📚 制度萌芽时代'
    if any(row.get('chapter') == 3 for row in journal.city_cases.values()):
        return 2, '🗞️ 城市记忆时代'
    if journal.buildings:
        return 1, '🏗️ 猴山建设时代'
    return 0, '🌱 猴山萌芽时代'


def evolution_report(journal: object, laws=None, relationships=None,
                     first: int = 0, second: int = 1) -> str:
    era, title = evolution_era(journal)
    result = [f'📜 文明纪元 {era}/4 · {title}',
              f'已记录 {len(journal.legacy_events)}/{MAX_LEGACY} 次不可重复的历史抉择。']
    for event_id, event in LEGACY_EVENTS.items():
        recorded = next((entry for entry in journal.legacy_events
                         if entry['event'] == event_id), None)
        if recorded:
            route = event.choices[ROUTES.index(recorded['route'])]
            result.append(f'✅ {event.title}：{route}')
        else:
            enabled, reason = legacy_status(event_id, journal, laws,
                                            relationships, first, second)
            result.append(f'{"🟢" if enabled else "🔒"} {event.title} · {reason}')
    return '\n'.join(result)
