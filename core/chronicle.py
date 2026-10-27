"""Opt-in, fictional monkey colony chronicle: bounded offline JSON, no telemetry.

A real-world user click is never stored. Only in-app fictional monkey events
with integer pet indices enter the chronicle. Scenes commit at completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile

MAX_EVENTS = 100
MAX_CASES = 12
MAX_POINTS = 9999
KINDS = ('banana', 'exam', 'rocket', 'sleep')
TRIGGERS = {
    'banana_duel': 'banana',
    'meeting': 'exam',
    'invention': 'rocket',
    'launch': 'rocket',
    'roll_call': 'sleep',
    'sleep_machine': 'sleep',
}
TITLES = {
    'banana': '🍌 消失的香蕉',
    'exam': '📚 猴山考试周',
    'rocket': '🚀 不靠谱的试飞计划',
    'sleep': '💤 消失的出勤记录',
}
# Each beat has two poses + two non-personal dialogue lines. Nothing here
# executes programs, touches real files or reads desktop/window content.
# chapters 0-1 investigate; chapter 2 depends on the relationship at playback.
CHAPTERS = {
    'banana': (
        (('blink', '香蕉不见了，现场却有一张收据。'), ('angry', '那张收据上的名字不是我的！'),
         ('idle', '先把线索登记进猴山档案。'), ('blink', '好，但是别再偷吃证据。')),
        (('walk', '监控拍不到，香蕉皮却会说话。'), ('blink', '我只发现一串奇怪的脚印。'),
         ('angry', '嫌疑猴名单越写越长了。'), ('idle', '别急，至少谜题变得有趣了。')),
    ),
    'exam': (
        (('blink', '猴山的考试卷竟然自己改分了。'), ('wake', '答案写着：以上皆是猴。'),
         ('idle', '我们先找出原始试卷。'), ('blink', '别把香蕉汁滴在证据上。')),
        (('angry', '原来有人把练习题当成了标准答案！'), ('blink', '别紧张，错误总能重做。'),
         ('wake', '现在得召开一场复核会议。'), ('idle', '会议也可以开得短一点。')),
    ),
    'rocket': (
        (('wake', '火箭还没起飞，申请表先上天了。'), ('blink', '这是无纸化办公的未来。'),
         ('angry', '必须补交安全说明。'), ('idle', '我给它加一根备用香蕉。')),
        (('blink', '第二次试飞：推进器方向似乎反了。'), ('fall', '不是倒飞，是重力创新。'),
         ('idle', '我们先做地面试验。'), ('wake', '这次的试验台不会跑路。')),
    ),
    'sleep': (
        (('wake', '签到表写着全员到齐。'), ('sleep', '我确实梦见自己准时上班。'),
         ('blink', '请解释梦境与考勤的区别。'), ('idle', '最大的区别是梦里有香蕉。')),
        (('angry', '机器算出睡眠时间超过一天。'), ('blink', '它把打盹算成了深度研究。'),
         ('idle', '我们应该先校准时钟。'), ('wake', '或者批准午睡合法化。')),
    ),
}
GOOD_ENDING = (
    ('wake', '误会解开了！猴山继续合作研究。'),
    ('blink', '那我们把这件事写成一份报告。'),
    ('idle', '结案：信任比香蕉还稀缺。'),
    ('wake', '这次终于没再丢证据。'),
)
CHAOS_ENDING = (
    ('angry', '调查结束，结果是所有猴都不服。'),
    ('blink', '那就下次重新投票吧！'),
    ('idle', '结案：档案暂存，争议保留。'),
    ('wake', '至少故事比会议有趣。'),
)


def _index(value: object) -> bool:
    return type(value) is int and 0 <= value < 6


def _bounded(value: object, maximum: int) -> int:
    return max(0, min(maximum, value)) if type(value) is int else 0


def _valid_pair(a: object, b: object) -> bool:
    return _index(a) and _index(b) and a != b


@dataclass(frozen=True)
class Chapter:
    case_id: int
    kind: str
    title: str
    chapter: int
    first: int
    second: int
    opening: tuple[tuple[str, str], tuple[str, str]]
    ending: tuple[tuple[str, str], tuple[str, str]]
    branch: str  # good, chaos, or continuing


class ChronicleStore:
    """Explicitly enabled, fictional continuity across program restarts."""

    def __init__(self, path: Path, *, enabled: bool = False) -> None:
        self.path = Path(path)
        self.enabled = bool(enabled)
        self.next_id = 1
        self.cases: list[dict] = []
        self.events: list[dict] = []
        self.growth: dict[str, dict[str, int]] = {}
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(payload, dict) or payload.get('version') != 1:
            return
        raw_cases = payload.get('cases', [])
        seen: set[int] = set()
        if isinstance(raw_cases, list):
            for item in raw_cases[-MAX_CASES:]:
                if not isinstance(item, dict):
                    continue
                cid, kind = item.get('id'), item.get('kind')
                a, b, stage = item.get('first'), item.get('second'), item.get('stage')
                if (type(cid) is not int or cid <= 0 or cid > 1_000_000_000 or
                        cid in seen or kind not in KINDS or not _valid_pair(a, b) or
                        type(stage) is not int or not 0 <= stage <= 3):
                    continue
                self.cases.append(dict(id=cid, kind=kind, first=a, second=b, stage=stage))
                seen.add(cid)
        self.next_id = max([1, _bounded(payload.get('next_id'), 1_000_000_000)] +
                           [c['id'] + 1 for c in self.cases])
        events = payload.get('events', [])
        if isinstance(events, list):
            for e in events[-MAX_EVENTS:]:
                if (isinstance(e, dict) and type(e.get('case_id')) is int
                        and e.get('kind') in KINDS
                        and type(e.get('chapter')) is int and 0 <= e['chapter'] <= 3
                        and e.get('event') in ('opened', 'completed')):
                    self.events.append({k: e[k] for k in ('case_id', 'kind', 'chapter', 'event')})
        growth = payload.get('growth', {})
        if isinstance(growth, dict):
            for k in ('0', '1', '2', '3', '4', '5'):
                row = growth.get(k)
                if isinstance(row, dict):
                    self.growth[k] = {
                        stat: _bounded(row.get(stat), MAX_POINTS)
                        for stat in ('research', 'mischief', 'empathy')
                    }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.chronicle-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'next_id': self.next_id,
                           'cases': self.cases, 'events': self.events,
                           'growth': self.growth}, stream, ensure_ascii=False, indent=2)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _log(self, item: dict) -> None:
        self.events.append(item)
        self.events = self.events[-MAX_EVENTS:]

    def observe(self, trigger: str, first: int, second: int) -> int | None:
        """Open a follow-up case only after an actual finished monkey event."""
        kind = TRIGGERS.get(trigger)
        if not self.enabled or kind is None or not _valid_pair(first, second):
            return None
        pair = {first, second}
        if any(c['kind'] == kind and c['stage'] < 3 and
               {c['first'], c['second']} == pair for c in self.cases):
            return None
        # Bounded: do not silently evict unfinished stories.
        if len(self.cases) >= MAX_CASES:
            for i, case in enumerate(self.cases):
                if case['stage'] == 3:
                    self.cases.pop(i)
                    break
            else:
                return None
        if self.next_id > 1_000_000_000:
            return None
        case = dict(id=self.next_id, kind=kind,
                    first=first, second=second, stage=0)
        self.next_id += 1
        self.cases.append(case)
        self._log(dict(case_id=case['id'], kind=kind, chapter=0, event='opened'))
        self._save()
        return case['id']

    def pending(self, *, member_count: int = 6) -> list[dict]:
        if not self.enabled or type(member_count) is not int:
            return []
        return [dict(c, title=TITLES[c['kind']]) for c in self.cases
                if c['stage'] < 3 and c['first'] < member_count
                and c['second'] < member_count]

    def preview(self, case_id: int, relation: dict | None = None) -> Chapter | None:
        """Pure preview; cancellation never changes progress or memory."""
        if not self.enabled or type(case_id) is not int:
            return None
        case = next((c for c in self.cases if c['id'] == case_id and c['stage'] < 3), None)
        if case is None:
            return None
        kind, stage = case['kind'], case['stage']
        if stage < 2:
            script = CHAPTERS[kind][stage]
            branch = 'continuing'
        else:
            rel = relation if isinstance(relation, dict) else {}
            # Only two endings, chosen from the existing fictional relationship.
            good = (_bounded(rel.get('trust'), 100) >= 20 and
                    type(rel.get('bond')) is int and rel['bond'] >= 15)
            script = GOOD_ENDING if good else CHAOS_ENDING
            branch = 'good' if good else 'chaos'
        return Chapter(case_id, kind, TITLES[kind], stage,
                       case['first'], case['second'],
                       ((script[0], script[1])), ((script[2], script[3])), branch)

    def complete(self, chapter: Chapter) -> bool:
        """Exactly once: stale/duplicate/dropped chapters never earn progress."""
        if not self.enabled or not isinstance(chapter, Chapter):
            return False
        case = next((c for c in self.cases if c['id'] == chapter.case_id), None)
        if case is None or case['stage'] != chapter.chapter or case['kind'] != chapter.kind:
            return False
        if case['first'] != chapter.first or case['second'] != chapter.second:
            return False
        # Treat caller's chapter as untrusted: require it to be a valid template
        # at that stage so fabricated achievements cannot be injected.
        expected = self.preview(chapter.case_id,
                                {'trust': 100, 'bond': 100} if chapter.branch == 'good' else {})
        if chapter != expected:
            return False
        case['stage'] += 1
        self._log(dict(case_id=case['id'], kind=case['kind'],
                       chapter=case['stage'], event='completed'))
        stat = {'banana': 'mischief', 'exam': 'research',
                'rocket': 'research', 'sleep': 'empathy'}[case['kind']]
        for index in (case['first'], case['second']):
            row = self.growth.setdefault(str(index), dict(research=0, mischief=0, empathy=0))
            row[stat] = min(MAX_POINTS, row[stat] + 1)
        self._save()
        return True

    def growth_for(self, index: int) -> dict[str, int | str]:
        if not _index(index):
            raise ValueError('invalid monkey index')
        row = self.growth.get(str(index), {})
        scores = {k: _bounded(row.get(k), MAX_POINTS) for k in ('research', 'mischief', 'empathy')}
        best = max(scores, key=lambda k: scores[k])
        titles = {'research': '实验室骨干', 'mischief': '香蕉观察员', 'empathy': '猴山调解员'}
        total = sum(scores.values())
        return {**scores, 'level': 1 + min(9, total // 4),
                'title': titles[best] if total else '见习猴'}

    def clear(self) -> None:
        self.cases.clear()
        self.events.clear()
        self.growth.clear()
        self.next_id = 1
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
