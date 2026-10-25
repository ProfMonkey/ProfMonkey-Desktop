"""Short, synchronized, finite *visual* stories shared by independent pets.

No screen/keyboard reading, no desktop file operations, no pet spawning.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class GroupBeat:
    seconds: float
    first: tuple[str, str]
    second: tuple[str, str]
    others: tuple[str, str] = ('idle', '围观中 🍌')


SCENES: dict[str, tuple[GroupBeat, ...]] = {
    'meeting': (
        GroupBeat(1.8, ('idle', '猴学委员会正式开会！'), ('blink', '本次议题：香蕉归属。')),
        GroupBeat(2.1, ('blink', '教授认为：1+1=猴。'), ('angry', '证据呢？'), ('idle', '做会议纪要。')),
        GroupBeat(2.0, ('eat_banana', '证据已经被我吃了。'), ('fall', '学术事故！'), ('blink', '全票通过？')),
        GroupBeat(1.8, ('idle', '本次会议圆满结束。'), ('sleep', '我投弃权票。'), ('idle', '散会散会！')),
    ),
    'banana_duel': (
        GroupBeat(1.6, ('eat_banana', '这里有一根香蕉！'), ('blink', '我也看见了！')),
        GroupBeat(2.0, ('walk', '先到先得！'), ('run', '规则临时修改！'), ('angry', '不要推我！')),
        GroupBeat(2.2, ('angry', '香蕉去哪了？'), ('eat_banana', '已完成内部消化。'), ('blink', '🍌')),
        GroupBeat(1.8, ('fall', '我申请重新分配！'), ('idle', '驳回。'), ('sleep', '下次一定。')),
    ),
}


class GroupStory:
    def __init__(self) -> None:
        self.name: str = ''
        self.index = 0
        self.elapsed = 0.0

    @property
    def active(self) -> bool:
        return self.name in SCENES

    @property
    def beat(self) -> GroupBeat | None:
        return SCENES[self.name][self.index] if self.active else None

    def start(self, name: str, count: int) -> bool:
        if self.active or name not in SCENES or count < 2:
            return False
        self.name, self.index, self.elapsed = name, 0, 0.0
        return True

    def advance(self, dt: float) -> bool:
        """Advance time; return True if the action beat has changed/ended."""
        if not 0 <= dt <= .5:
            raise ValueError('invalid group-story delta')
        if not self.active:
            return False
        self.elapsed += dt
        if self.elapsed < self.beat.seconds:
            return False
        self.elapsed -= self.beat.seconds
        self.index += 1
        if self.index >= len(SCENES[self.name]):
            self.cancel()
        return True

    def cancel(self) -> None:
        self.name, self.index, self.elapsed = '', 0, 0.0
