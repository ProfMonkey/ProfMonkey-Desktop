"""Manual, offline monkey society. Pure fictional votes & relationship factions.

No keyboard/window/system inspection and no user profiling. All outcomes are
deterministic from in-app monkey personalities and fictional relationship data.
"""
from __future__ import annotations
from dataclasses import dataclass

ISSUES = {
    'banana_rules': ('🍌 香蕉配给条例', '猴山是否实行统一分配香蕉？'),
    'quiet_hours': ('🌙 猴山静音公约', '晚上是否禁止大声敲实验设备？'),
    'rocket_license': ('🚀 火箭试飞许可', '发明猴的火箭是否获得试飞资格？'),
}
PERSONALITY_VIEWS: dict[str, dict[str, int]] = {
    'scholar':   {'banana_rules': 1,  'quiet_hours': 3,  'rocket_license': -1},
    'trickster': {'banana_rules': -3, 'quiet_hours': -3, 'rocket_license': 2},
    'sleepy':   {'banana_rules': 0,  'quiet_hours': 3,  'rocket_license': -2},
    'inventor': {'banana_rules': -1, 'quiet_hours': -1, 'rocket_license': 3},
    'captain':  {'banana_rules': 3,  'quiet_hours': 1,  'rocket_license': -2},
    'shy':      {'banana_rules': 1,  'quiet_hours': 3,  'rocket_license': -1},
}
VOTE_NAMES = {'yes': '支持', 'no': '反对', 'abstain': '弃权'}
RESULT_NAMES = {
    'adopted': '议案通过',
    'rejected': '议案否决',
    'stalemate': '猴山暂时僵持',
}


@dataclass(frozen=True)
class Seat:
    index: int
    personality: str


@dataclass(frozen=True)
class CouncilBeat:
    seconds: float
    poses: tuple[tuple[int, str, str], ...]


@dataclass(frozen=True)
class CouncilPlan:
    issue: str
    seats: tuple[Seat, ...]
    votes: tuple[tuple[int, str], ...]
    result: str
    beats: tuple[CouncilBeat, ...]


def _validate_seats(seats: tuple[Seat, ...]) -> None:
    if not 3 <= len(seats) <= 6:
        raise ValueError('a council requires 3–6 monkeys')
    ids = [s.index for s in seats]
    if any(type(i) is not int or not 0 <= i < 6 for i in ids):
        raise ValueError('invalid seat ID')
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate seats')
    if any(s.personality not in PERSONALITY_VIEWS for s in seats):
        raise ValueError('invalid personality')


def _relationship(relations, first: int, second: int) -> dict:
    if relations is None:
        return {}
    values = relations.get(first, second)
    return values if isinstance(values, dict) else {}


def _bounded_relation(raw: object, low: int, high: int) -> int:
    return max(low, min(high, raw)) if type(raw) is int else 0


def _sentiment(relations, a: int, b: int) -> tuple[bool, bool]:
    relation = _relationship(relations, a, b)
    bond = _bounded_relation(relation.get('bond'), -100, 100)
    trust = _bounded_relation(relation.get('trust'), 0, 100)
    rivalry = _bounded_relation(relation.get('rivalry'), 0, 100)
    return (bond >= 35 and trust >= 30 and rivalry < 55,
            rivalry >= 55 or bond <= -35)


def derive_factions(seats: tuple[Seat, ...], relations=None) -> tuple[tuple[int, ...], ...]:
    """Connected components of strong friendship, 2+ monkeys; not permanent labels.

    A new friendship can join two groups. Broken friendship removes edges on
    the next snapshot. A rivalry never becomes a friendship by transitivity.
    """
    if not 1 <= len(seats) <= 6:
        raise ValueError('invalid colony size')
    ids = [s.index for s in seats]
    if any(type(i) is not int or not 0 <= i < 6 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('duplicate or invalid colony members')
    root = {i: i for i in ids}

    def find(v: int) -> int:
        while root[v] != v:
            v = root[v]
        return v

    for n, a in enumerate(ids):
        for b in ids[n + 1:]:
            friendly, _ = _sentiment(relations, a, b)
            if friendly:
                root[find(max(a, b))] = find(min(a, b))
    clusters: dict[int, list[int]] = {}
    for i in ids:
        clusters.setdefault(find(i), []).append(i)
    return tuple(sorted((tuple(sorted(group)) for group in clusters.values()
                         if len(group) >= 2), key=lambda group: group[0]))


def prepare_council(issue: str, seats: tuple[Seat, ...],
                    relations=None) -> CouncilPlan:
    if issue not in ISSUES:
        raise ValueError('unknown council issue')
    _validate_seats(seats)
    # One instantaneous snapshot: everyone votes once. Friendship/rivalry
    # influences the view by one point, without vote-order feedback loops.
    votes: list[tuple[int, str]] = []
    for member in seats:
        score = PERSONALITY_VIEWS[member.personality][issue] * 3
        for peer in seats:
            if member.index == peer.index:
                continue
            friend, rival = _sentiment(relations, member.index, peer.index)
            preferred = PERSONALITY_VIEWS[peer.personality][issue]
            sign = (preferred > 0) - (preferred < 0)
            if friend:
                score += sign
            elif rival:
                score -= sign
        if score > 0:
            vote = 'yes'
        elif score < 0:
            vote = 'no'
        else:
            vote = 'abstain'
        votes.append((member.index, vote))
    yes = sum(value == 'yes' for _, value in votes)
    no = sum(value == 'no' for _, value in votes)
    if yes > len(seats) // 2:
        result = 'adopted'
    elif no > len(seats) // 2:
        result = 'rejected'
    else:
        result = 'stalemate'

    chair = seats[0].index
    introduction = tuple(
        (member.index, 'wake' if member.index == chair else 'blink',
         ISSUES[issue][1] if member.index == chair else
         '先听听大家的理由。' if member.personality in ('scholar', 'shy') else
         '这事得好好讨论。')
        for member in seats
    )
    ballot = tuple(
        (index, 'wake' if vote == 'yes' else 'angry' if vote == 'no' else 'sleep',
         '这一票我支持！' if vote == 'yes' else
         '这一票我反对！' if vote == 'no' else '我决定保留意见。')
        for index, vote in votes
    )
    closing = tuple(
        (member.index, 'wake' if result == 'adopted' else
         'angry' if result == 'rejected' else 'blink',
         f'{RESULT_NAMES[result]}：{yes}票支持、{no}票反对。'
         if member.index == chair else
         '尊重结果，准备下一次实验。' if result == 'adopted' else
         '这条规定还得重新讨论。' if result == 'rejected' else
         '僵持不下，先吃香蕉再议。')
        for member in seats
    )
    return CouncilPlan(issue, seats, tuple(votes), result, (
        CouncilBeat(2.0, introduction),
        CouncilBeat(2.2, ballot),
        CouncilBeat(2.1, closing),
    ))


class CouncilStory:
    """Finite 3-beat timer. Only an explicit completed state may be committed."""

    def __init__(self) -> None:
        self.plan: CouncilPlan | None = None
        self.index = 0
        self.elapsed = 0.0

    @property
    def active(self) -> bool:
        return self.plan is not None

    @property
    def finished(self) -> bool:
        return self.active and self.index >= len(self.plan.beats)

    @property
    def beat(self) -> CouncilBeat | None:
        if not self.active or self.finished:
            return None
        return self.plan.beats[self.index]

    def start(self, plan: CouncilPlan) -> bool:
        if self.active or not isinstance(plan, CouncilPlan):
            return False
        self.plan = plan
        self.index = 0
        self.elapsed = 0.0
        return True

    def advance(self, dt: float) -> bool:
        if not isinstance(dt, (int, float)) or not 0 <= dt <= .5:
            raise ValueError('invalid council delta')
        if not self.active or self.finished:
            return False
        self.elapsed += dt
        if self.elapsed < self.beat.seconds:
            return False
        self.elapsed -= self.beat.seconds
        self.index += 1
        return True

    def cancel(self) -> None:
        self.plan = None
        self.index = 0
        self.elapsed = 0.0
