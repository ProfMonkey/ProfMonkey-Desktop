"""Opt-in, low-frequency autonomous encounters between desktop monkeys.

Only consumes in-app monkey positions, personalities and fictional relationships.
Never reads desktop, process, mouse, keyboard, or application content.
"""
from __future__ import annotations
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Participant:
    index: int
    x: float  # on-screen rendered sprite center (not window top-left)
    y: float
    personality: str
    busy: bool = False


@dataclass(frozen=True)
class Encounter:
    first: int
    second: int
    kind: str
    action_first: str
    action_second: str
    line_first: str
    line_second: str


class EncounterDirector:
    """Deterministic gatekeeper with pair + global cooldown and no task loops."""
    def __init__(self, *, seed: int = 20261026, pair_cooldown: float = 240.0,
                 global_cooldown: float = 120.0, max_distance: float = 90.0) -> None:
        self.rng = random.Random(seed)
        self.pair_cooldown = float(pair_cooldown)
        self.global_cooldown = float(global_cooldown)
        self.max_distance = float(max_distance)
        self.last_global = float('-inf')
        self.last_pair: dict[tuple[int, int], float] = {}

    def clear(self) -> None:
        self.last_pair.clear()
        self.last_global = float('-inf')

    def _kind(self, a: Participant, b: Participant, relation: dict) -> str:
        if relation.get('rivalry', 0) >= 55:
            return 'debate'
        if relation.get('bond', 0) >= 35 and relation.get('trust', 0) >= 30:
            return 'high_five'
        if 'sleepy' in (a.personality, b.personality):
            return 'nap'
        if 'trickster' in (a.personality, b.personality) and self.rng.random() < .55:
            return 'prank'
        return 'hello'

    @staticmethod
    def _script(a: Participant, b: Participant, kind: str) -> Encounter:
        lines = {
            'debate': ('angry', 'angry', '我宣布你这篇论文不合格！', '你连香蕉引用都没有！'),
            'high_five': ('wake', 'blink', '猴山双强，击掌！', '这次实验居然成功了！'),
            'nap': ('sleep', 'blink', '论文先放放，睡五分钟。', '五分钟？你上次睡到周一！'),
            'prank': ('blink', 'angry', '你背后有一根会写代码的香蕉！', '不要拿学术问题开玩笑！'),
            'hello': ('blink', 'wake', '早上好，今天研究什么？', '研究为什么猴子还没下班。'),
        }
        act_a, act_b, line_a, line_b = lines[kind]
        return Encounter(a.index, b.index, kind, act_a, act_b, line_a, line_b)

    def choose(self, now: float, participants: list[Participant], relations,
               *, force: bool = False) -> Encounter | None:
        """Pick one eligible pair. ``force`` bypasses distance/cooldown for a manual demo."""
        if len(participants) < 2 or (not force and now < self.last_global + self.global_cooldown):
            return None
        eligible = [p for p in participants if not p.busy]
        choices = []
        for i, a in enumerate(eligible):
            for b in eligible[i + 1:]:
                key = (min(a.index, b.index), max(a.index, b.index))
                distance_sq = (a.x - b.x)**2 + (a.y - b.y)**2
                if not force and (distance_sq > self.max_distance**2 or
                                  now < self.last_pair.get(key, float('-inf')) + self.pair_cooldown):
                    continue
                choices.append((distance_sq, key, a, b))
        if not choices:
            return None
        _, key, a, b = min(choices, key=lambda e: (e[0], e[1]))
        relation = relations.get(a.index, b.index) if relations is not None else {}
        kind = self._kind(a, b, relation)
        event = self._script(a, b, kind)
        self.last_global = now
        self.last_pair[key] = now
        # Prune old cooldowns to keep state bounded with small monkey count.
        self.last_pair = {k: t for k, t in self.last_pair.items()
                          if now - t <= self.pair_cooldown}
        return event
