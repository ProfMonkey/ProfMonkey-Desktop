"""Offline, user-triggered, three-act monkey missions and bounded local resources.

All time is in in-game scene seconds. No OS inspection, network, GPS, real
economy or background scheduling; only completed cartoon shows earn rewards.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile

from core.civilization import (BUILDINGS, construction_status, city_tier,
                               mission_city_bonus, sanitize_city)
from core.city_life import (CASE_TITLES, CityPlan, MAX_CASE_NEWS, case_delta,
                            empty_case, normalize_cases)
from core.city_evolution import (EvolutionPlan, clean_legacy, prepare_evolution,
                                 evolution_era, LEGACY_EVENTS)

MISSIONS = {
    'banana_scout': ('🍌 香蕉侦察队', '在猴山寻找传说中的香蕉树'),
    'meteor_lab': ('🔭 陨石研究所', '研究来自银河猴山的奇怪矿石'),
    'village_repair': ('🏡 猴山营造队', '修建猴山公共长椅与小桥'),
}
SKILLS = {
    'scholar': (1, 3, 2), 'trickster': (3, 0, 1),
    'sleepy': (0, 0, 2), 'inventor': (2, 3, 1),
    'captain': (1, 1, 3), 'shy': (2, 2, 3),
}
LAW_BONUS = {
    'banana_scout': 'banana_rules',
    'meteor_lab': 'rocket_license',
    'village_repair': 'quiet_hours',
}
REWARDS = {
    'banana_scout': {'success': (5, 1, 1), 'mixed': (2, 0, 1), 'mishap': (0, 0, 0)},
    'meteor_lab': {'success': (0, 5, 2), 'mixed': (0, 2, 1), 'mishap': (0, 0, 0)},
    'village_repair': {'success': (1, 1, 5), 'mixed': (0, 0, 2), 'mishap': (0, 0, 0)},
}
RESULTS = {'success': '大功告成', 'mixed': '差点成功', 'mishap': '猴山事故'}
RESOURCE_KEYS = ('bananas', 'science', 'reputation')
MAX_VALUE = 999
MAX_LOG = 36
BLUEPRINTS = (
    ('banana_vault', '🍌 香蕉研究仓库', (12, 0, 0)),
    ('galaxy_scope', '🔭 银河猴山望远镜', (0, 12, 0)),
    ('public_square', '🏛️ 猴山公共广场', (0, 0, 12)),
    ('monkey_academy', '🌌 银河猴山联合实验室', (20, 20, 20)),
)


@dataclass(frozen=True)
class Explorer:
    index: int
    personality: str


@dataclass(frozen=True)
class ExpeditionBeat:
    seconds: float
    poses: tuple[tuple[int, str, str], ...]


@dataclass(frozen=True)
class ExpeditionPlan:
    mission: str
    crew: tuple[Explorer, ...]
    outcome: str
    rewards: tuple[int, int, int]
    score: int
    beats: tuple[ExpeditionBeat, ...]
    law_boost: bool = False
    city_buildings: frozenset[str] = frozenset()


def _bounded(value: object) -> int:
    return max(0, min(MAX_VALUE, value)) if type(value) is int else 0


def _validate_crew(crew: tuple[Explorer, ...]) -> None:
    if type(crew) is not tuple or not 2 <= len(crew) <= 6:
        raise ValueError('2-6 explorers required')
    seen = set()
    for member in crew:
        if (not isinstance(member, Explorer) or type(member.index) is not int
                or not 0 <= member.index < 6 or member.index in seen
                or type(member.personality) is not str or member.personality not in SKILLS):
            raise ValueError('invalid/duplicate explorer')
        seen.add(member.index)


def _synergy(relations, left: int, right: int) -> int:
    if relations is None:
        return 0
    pair = relations.get(left, right)
    if not isinstance(pair, dict):
        return 0
    bond, trust, rivalry = pair.get('bond'), pair.get('trust'), pair.get('rivalry')
    if any(type(v) is not int for v in (bond, trust, rivalry)):
        return 0
    if rivalry >= 55 or bond <= -35:
        return -1
    return 1 if bond >= 35 and trust >= 30 else 0


def plan_expedition(mission: str, crew: tuple[Explorer, ...],
                    relationships=None, active_laws: frozenset[str] = frozenset(),
                    built: frozenset[str] = frozenset()) -> ExpeditionPlan:
    if type(mission) is not str or mission not in MISSIONS:
        raise ValueError('unknown mission')
    _validate_crew(crew)
    if not isinstance(active_laws, frozenset):
        raise ValueError('laws must be snapshotted')
    if not isinstance(built, frozenset) or sanitize_city(list(built)) != built:
        raise ValueError('invalid city buildings snapshot')
    skill = tuple(MISSIONS).index(mission)
    score = sum(SKILLS[member.personality][skill] for member in crew)
    for i, person in enumerate(crew):
        for partner in crew[i+1:]:
            score += _synergy(relationships, person.index, partner.index)
    boosted = LAW_BONUS[mission] in active_laws
    city_score, _ = mission_city_bonus(mission, built)
    score += city_score + (2 if boosted else 0)
    outcome = 'success' if score >= 6 else 'mixed' if score >= 3 else 'mishap'
    rewards = list(REWARDS[mission][outcome])
    if boosted and outcome != 'mishap':
        rewards[skill] += 1
    _, city_rewards = mission_city_bonus(mission, built, outcome)
    rewards = [value + city_rewards[i] for i, value in enumerate(rewards)]
    first = tuple((p.index, 'wake' if n == 0 else 'blink',
                   f'{MISSIONS[mission][0]}集合！' if n == 0 else '装备清点完成！')
                  for n, p in enumerate(crew))
    middle = tuple((p.index, 'run' if n % 2 == 0 else 'walk',
                    '这里有一条新线索！' if p.personality in ('scholar', 'shy') else
                    '交给我的神奇工具！' if p.personality == 'inventor' else
                    '我闻到了香蕉味。' if p.personality == 'trickster' else
                    '我来负责安全。' if p.personality == 'captain' else
                    '这个任务有午睡时间吗？')
                   for n, p in enumerate(crew))
    ending = tuple((p.index,
                    'wake' if outcome == 'success' else 'blink' if outcome == 'mixed' else 'fall',
                    ('任务成功！猴山资源增加了。' if outcome == 'success' else
                     '出了一点差错，但还是带回了收获。' if outcome == 'mixed' else
                     '今天没找到资源，大家平安就好。') if n == 0 else
                    '下次继续合作！' if outcome != 'mishap' else '先收拾装备回家吧。')
                   for n, p in enumerate(crew))
    return ExpeditionPlan(mission, crew, outcome, tuple(rewards), score,
                          (ExpeditionBeat(1.7, first), ExpeditionBeat(2.1, middle),
                           ExpeditionBeat(1.9, ending)), boosted, built)


class ExpeditionStory:
    def __init__(self) -> None:
        self.plan: ExpeditionPlan | None = None
        self.index = 0
        self.elapsed = 0.
        self._committed = False

    @property
    def active(self) -> bool:
        return self.plan is not None

    @property
    def finished(self) -> bool:
        return self.active and self.index >= len(self.plan.beats)

    @property
    def beat(self) -> ExpeditionBeat | None:
        return self.plan.beats[self.index] if self.active and not self.finished else None

    def start(self, plan: ExpeditionPlan) -> bool:
        if self.active or not isinstance(plan, ExpeditionPlan):
            return False
        try:
            _validate_crew(plan.crew)
        except ValueError:
            return False
        if type(plan.mission) is not str or plan.mission not in MISSIONS or len(plan.beats) != 3:
            return False
        self.plan, self.index, self.elapsed, self._committed = plan, 0, 0., False
        return True

    def advance(self, dt: float) -> bool:
        if type(dt) not in (float, int) or not 0 <= dt <= .5:
            raise ValueError('invalid expedition delta')
        if not self.active or self.finished:
            return False
        self.elapsed += dt
        if self.elapsed < self.beat.seconds:
            return False
        self.elapsed -= self.beat.seconds
        self.index += 1
        return True

    def consume_completion(self) -> bool:
        if not self.finished or self._committed:
            return False
        self._committed = True
        return True

    def cancel(self) -> None:
        self.plan, self.index, self.elapsed, self._committed = None, 0, 0., False


class ExpeditionJournal:
    """Separate, atomic, bounded, explicitly erasable fictional scorebook."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.resources = {key: 0 for key in RESOURCE_KEYS}
        self.missions = {i: 0 for i in range(6)}
        self.buildings: frozenset[str] = frozenset()
        self.city_cases: dict[str, dict] = {key: empty_case() for key in CASE_TITLES}
        self.city_news: list[dict] = []
        self.legacy_events: list[dict[str, str]] = []
        self.log: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, TypeError, ValueError):
            return
        if not isinstance(raw, dict) or raw.get('version') != 1:
            return
        # Legacy v0.15 journals contain no building data; keep full backward
        # compatibility while accepting only four known completed structures.
        self.buildings = sanitize_city(raw.get('buildings'))
        self.city_cases = normalize_cases(raw.get('city_cases'), self.buildings)
        self.legacy_events = clean_legacy(raw.get('legacy_events'),
                                          self.city_cases, self.buildings)
        raw_news = raw.get('city_news')
        if isinstance(raw_news, list):
            for row in raw_news[-MAX_CASE_NEWS:]:
                if not isinstance(row, dict):
                    continue
                case, chapter = row.get('case'), row.get('chapter')
                choice, ending = row.get('choice'), row.get('ending')
                if (type(case) is str and case in CASE_TITLES and case in self.buildings
                        and type(chapter) is int and 1 <= chapter <= 3
                        and type(choice) is str and choice in ('careful','bold')
                        and type(ending) is str and ending in ('','reconciled','chaos')):
                    self.city_news.append({'case':case,'chapter':chapter,
                                           'choice':choice,'ending':ending})
        resources = raw.get('resources')
        if isinstance(resources, dict):
            for k in RESOURCE_KEYS:
                self.resources[k] = _bounded(resources.get(k))
        counts = raw.get('missions')
        if isinstance(counts, dict):
            for i in range(6):
                self.missions[i] = _bounded(counts.get(str(i)))
        log = raw.get('log')
        if isinstance(log, list):
            for row in log[-MAX_LOG:]:
                if not isinstance(row, dict):
                    continue
                kind, outcome, team = row.get('mission'), row.get('outcome'), row.get('crew')
                if (type(kind) is str and kind in MISSIONS and type(outcome) is str
                        and outcome in RESULTS and isinstance(team, list)
                        and 2 <= len(team) <= 6 and
                        all(type(i) is int and 0 <= i < 6 for i in team)
                        and len(set(team)) == len(team)):
                    self.log.append({'mission': kind, 'outcome': outcome, 'crew': team})

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(dir=self.path.parent, prefix='.expedition-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'resources': self.resources,
                           'missions': {str(i): self.missions[i] for i in range(6)},
                           'buildings': sorted(self.buildings),
                           'city_cases': self.city_cases,
                           'city_news': self.city_news,
                           'legacy_events': self.legacy_events,
                           'log': self.log}, stream, ensure_ascii=False, indent=2)
            os.replace(path, self.path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def record(self, plan: ExpeditionPlan) -> bool:
        """Call only after ExpeditionStory.consume_completion() is True."""
        if not isinstance(plan, ExpeditionPlan):
            return False
        try:
            _validate_crew(plan.crew)
            skill = tuple(MISSIONS).index(plan.mission)
        except (ValueError, TypeError):
            return False
        if (type(plan.outcome) is not str or plan.outcome not in RESULTS
                or type(plan.score) is not int or type(plan.law_boost) is not bool
                or not isinstance(plan.city_buildings, frozenset)
                or sanitize_city(list(plan.city_buildings)) != plan.city_buildings):
            return False
            return False
        base = REWARDS[plan.mission][plan.outcome]
        _score, city_rewards = mission_city_bonus(
            plan.mission, plan.city_buildings, plan.outcome)
        expected = tuple(n + (1 if plan.law_boost and i == skill and
                              plan.outcome != 'mishap' else 0)
                         + city_rewards[i] for i, n in enumerate(base))
        if plan.rewards != expected or len(plan.beats) != 3:
            return False
        expected_result = ('success' if plan.score >= 6 else
                           'mixed' if plan.score >= 3 else 'mishap')
        if plan.outcome != expected_result:
            return False
        for i, key in enumerate(RESOURCE_KEYS):
            self.resources[key] = min(MAX_VALUE, self.resources[key] + plan.rewards[i])
        for member in plan.crew:
            self.missions[member.index] = min(MAX_VALUE, self.missions[member.index] + 1)
        self.log.append({'mission': plan.mission, 'outcome': plan.outcome,
                         'crew': [member.index for member in plan.crew]})
        self.log = self.log[-MAX_LOG:]
        self._save()
        return True

    def unlocked(self) -> tuple[tuple[str, str], ...]:
        """Earned v0.15 achievement remains visible after a building is paid for."""
        totals = tuple(self.resources[k] for k in RESOURCE_KEYS)
        return tuple((key, label) for key, label, required in BLUEPRINTS
                     if key in self.buildings or
                     all(current >= minimum for current, minimum in zip(totals, required)))

    def construct(self, building: str) -> bool:
        """Pay and build in one atomic journal write; invalid attempts do nothing.

        No waiting/auto-build: the user explicitly confirms construction in UI.
        Roll memory back if disk save fails so no phantom building appears.
        """
        eligible, _reason = construction_status(
            building, self.resources, self.buildings)
        if not eligible:
            return False
        previous_balances = self.resources.copy()
        old_city = self.buildings
        spec = BUILDINGS[building]
        for name, cost in zip(RESOURCE_KEYS, spec.cost):
            self.resources[name] -= cost
        self.buildings = frozenset(set(self.buildings) | {building})
        try:
            self._save()
        except OSError:
            self.resources = previous_balances
            self.buildings = old_city
            return False
        return True

    def record_city_chapter(self, plan: CityPlan) -> bool:
        """Atomic in-game chapter progress + resource effect, once per chapter.

        Only a completed CityLifeStory may ask for this; optimistic chapter
        version check also defeats replay even if a caller repeats commit.
        """
        if not isinstance(plan, CityPlan):
            return False
        case = plan.case_id
        if type(case) is not str or case not in CASE_TITLES or case not in self.buildings:
            return False
        row = self.city_cases[case]
        expected = (row['chapter'], row['careful'], row['bold'])
        if (plan.expected_state != expected or type(plan.chapter) is not int or
                plan.chapter != row['chapter'] or plan.chapter >= 3 or
                type(plan.choice) is not str or plan.choice not in ('careful','bold') or
                type(plan.first) is not int or type(plan.second) is not int or
                plan.first == plan.second or not 0 <= plan.first < 6 or
                not 0 <= plan.second < 6 or len(plan.beats) != 3):
            return False
        if plan.resource_delta != case_delta(case, plan.choice):
            return False
        if ((plan.chapter < 2 and plan.ending is not None) or
                (plan.chapter == 2 and plan.ending not in ('reconciled','chaos'))):
            return False
        previous_resources = self.resources.copy()
        previous_case = row.copy()
        previous_news = list(self.city_news)
        for key, change in zip(RESOURCE_KEYS, plan.resource_delta):
            self.resources[key] = max(0, min(MAX_VALUE, self.resources[key] + change))
        row['chapter'] += 1
        row[plan.choice] += 1
        if plan.ending is not None:
            row['ending'] = plan.ending
        self.city_news.append({'case':case,'chapter':row['chapter'],
                               'choice':plan.choice,'ending':row['ending']})
        self.city_news = self.city_news[-MAX_CASE_NEWS:]
        try:
            self._save()
        except OSError:
            self.resources = previous_resources
            self.city_cases[case] = previous_case
            self.city_news = previous_news
            return False
        return True

    def record_evolution(self, plan: EvolutionPlan, laws=None,
                         relationships=None) -> bool:
        """Commit a manually completed v0.18 sequel and balances atomically.

        Validation runs again at settlement, so repealed laws, changed bonds,
        already-consumed events, forged deltas or cancelled plans cannot reuse
        a stale UI preview. The separately stored relationship effect is
        applied by the caller *only after* this commit succeeds.
        """
        if not isinstance(plan, EvolutionPlan):
            return False
        try:
            expected = prepare_evolution(plan.event_id, plan.route, self, laws,
                                         relationships, plan.first, plan.second)
        except (ValueError, KeyError, TypeError):
            return False
        if plan != expected:
            return False
        for key, change in zip(RESOURCE_KEYS, plan.resource_delta):
            if self.resources[key] + change < 0:
                return False
        old_resources = self.resources.copy()
        old_history = list(self.legacy_events)
        for key, change in zip(RESOURCE_KEYS, plan.resource_delta):
            self.resources[key] = min(MAX_VALUE, self.resources[key] + change)
        self.legacy_events.append({'event': plan.event_id, 'route': plan.route})
        try:
            self._save()
        except OSError:
            self.resources = old_resources
            self.legacy_events = old_history
            return False
        return True

    def clear(self) -> None:
        self.resources = {key: 0 for key in RESOURCE_KEYS}
        self.missions = {i: 0 for i in range(6)}
        self.buildings = frozenset()
        self.city_cases = {key: empty_case() for key in CASE_TITLES}
        self.city_news = []
        self.legacy_events = []
        self.log = []
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass


def newspaper(journal: ExpeditionJournal, laws=None, names: tuple[str, ...] = ()) -> str:
    """Create a fictional bulletin solely from the game's local data."""
    v = journal.resources
    _tier, title = city_tier(journal.buildings)
    rows = ['🗞️ 猴山日报 · 本期手工汇总',
            f'🍌 香蕉 {v["bananas"]} | 🔬 科研 {v["science"]} | ⭐ 声望 {v["reputation"]}',
            f'📦 最近保存 {len(journal.log)} 次探险',
            f'🏗️ 文明阶段：{title} · 已建建筑 {len(journal.buildings)}/4',
            f'🎬 城市事件已演出 {len(journal.city_news)} 章',
            f'📜 文明演化：{evolution_era(journal)[1]} · '
            f'历史抉择 {len(journal.legacy_events)}/{len(LEGACY_EVENTS)}']
    if laws is not None:
        active = [label for key, label in (
            ('banana_rules', '香蕉共享'), ('quiet_hours', '安静公约'),
            ('rocket_license', '火箭许可')) if laws.active(key)]
        rows.append('📜 已通过：' + ('、'.join(active) if active else '暂无法令'))
    for item in reversed(journal.log[-5:]):
        people = '、'.join(names[i] if i < len(names) else f'#{i + 1}'
                          for i in item['crew'])
        rows.append(f'• {MISSIONS[item["mission"]][0]}'
                    f' · {RESULTS[item["outcome"]]}（{people}）')
    if not journal.log:
        rows.append('今天还没有出任务。选择两只猴子试试！')
    leaders = sorted(((idx, count) for idx, count in journal.missions.items()
                      if count > 0), key=lambda row: (-row[1], row[0]))
    if leaders:
        rows.append('🏅 出勤榜：' + ' / '.join(
            f'{names[i] if i < len(names) else f"#{i+1}"} {count}次'
            for i, count in leaders[:3]))
    if journal.city_news:
        rows.append('🗞️ 最新城市事件：')
        for event in reversed(journal.city_news[-3:]):
            suffix = (' · 温暖结局' if event['ending']=='reconciled' else
                      ' · 混乱结局' if event['ending']=='chaos' else '')
            rows.append(f'• {CASE_TITLES[event["case"]]}'
                        f' 第{event["chapter"]}章{suffix}')
    if journal.legacy_events:
        rows.append('📚 最近历史抉择：')
        for event in reversed(journal.legacy_events[-3:]):
            label = LEGACY_EVENTS[event['event']].title
            route = '公开协作' if event['route'] == 'community' else '精英突破'
            rows.append(f'• {label} · {route}')
    rewards = journal.unlocked()
    rows.append('🏆 成果：' +
                ('、'.join(title for _key, title in rewards)
                 if rewards else '见习猴山'))
    return '\n'.join(rows)
