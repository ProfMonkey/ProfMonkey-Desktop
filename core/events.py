"""Cancelable, single-owner scripted mini-stories. No user desktop capture."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import random


@dataclass(frozen=True)
class Beat:
    action: str
    seconds: float
    prop: str = ''
    line: str = ''


SCRIPTS: dict[str, tuple[Beat, ...]] = {
    'banana': (
        Beat('eat_banana', 1.7, 'banana', '今日水果摄入 +1'),
        Beat('idle', 1.0, 'peel', '香蕉皮：暂存'),
        Beat('walk', 1.2, 'peel', '危险！'),
        Beat('slip', .65, 'peel', '？'),
        Beat('fall', .8, 'peel', '牛顿是对的'),
        Beat('get_up', .85, 'peel', '我没事'),
        Beat('angry', 1.8, 'sign', '都是你的问题！'),
    ),
    'banana_safe': (
        Beat('eat_banana', 1.7, 'banana', '今日水果摄入 +1'),
        Beat('idle', 1.0, 'peel', '香蕉皮：暂存'),
        Beat('blink', 1.0, 'peel', '这是谁丢的？'),
        Beat('idle', 1.6, '', '教授讲究卫生。'),
    ),
    'blackboard': (
        Beat('idle', 1.3, 'board', '教授授课'),
        Beat('blink', 2.3, 'board', '1 + 1 = 3'),
        Beat('angry', 1.4, 'board', '谁说不对？'),
        Beat('idle', 2.1, 'board', '1 + 1 = 猴'),
    ),
    'mirror': (
        Beat('idle', 1.5, 'mirror', '另一个我？'),
        Beat('turn', 1.4, 'mirror_twins', '我们认识吗？'),
        Beat('walk', 1.7, 'mirror_twins', '开会！'),
        Beat('idle', 1.5, 'mirror', '会议已散'),
    ),
    'keyboard': (
        Beat('idle', 1.5, 'keyboard', '打字速度：自信'),
        Beat('walk', 2.4, 'keyboard', '哒哒哒哒！'),
        Beat('fall', 1.4, 'keyboard_broken', '键盘阵亡'),
        Beat('idle', 2.2, 'banana', '用香蕉继续敲'),
    ),
    'edge': (
        Beat('walk', 1.3, '', '高处不胜寒'),
        Beat('slip', .7, '', '脚滑'),
        Beat('fall', 1.0, '', '...'),
        Beat('get_up', 1.2, '', '你什么都没看到'),
    ),
}


class StoryDirector:
    def __init__(self, seed: int = 42, on_finish: Callable[[str], None] | None = None) -> None:
        self.rng = random.Random(seed)
        self.name = ''
        self.steps: tuple[Beat, ...] = ()
        self.index = 0
        self.elapsed = 0.0
        self.on_finish = on_finish

    @property
    def active(self) -> bool:
        return bool(self.steps)

    @property
    def beat(self) -> Beat | None:
        return self.steps[self.index] if self.active else None

    def start(self, name: str, *, safe: bool | None = None) -> bool:
        if self.active or name not in SCRIPTS or name == 'banana_safe':
            return False
        if name == 'banana':
            safe = (self.rng.random() < .30) if safe is None else safe
            script = 'banana_safe' if safe else 'banana'
        else:
            script = name
        self.steps, self.index, self.elapsed, self.name = SCRIPTS[script], 0, 0., script
        return True

    def advance(self, dt: float) -> bool:
        """Return True if beat changed or story ended."""
        if not 0 <= dt <= .25:
            raise ValueError('invalid story delta')
        if not self.active:
            return False
        self.elapsed += dt
        old = self.index
        if self.elapsed >= self.steps[self.index].seconds:
            self.elapsed = 0.0
            self.index += 1
            if self.index >= len(self.steps):
                self.finish()
            return True
        return self.index != old

    def correct_blackboard(self) -> bool:
        """Clicking the erroneous equation jumps to the professor's correction."""
        if self.active and self.name == 'blackboard' and self.index in (1, 2):
            self.index = len(self.steps) - 1
            self.elapsed = 0.0
            return True
        return False

    def rescue_peel(self) -> bool:
        """User clicked during peel beat: safely branch before accident happens."""
        if self.name == 'banana' and self.active and self.beat.prop == 'peel' and self.index <= 2:
            self.name = 'banana_safe'
            self.steps = SCRIPTS['banana_safe'][2:]
            self.index = 0
            self.elapsed = 0.0
            return True
        return False

    def finish(self) -> None:
        previous = self.name
        self.name, self.steps, self.index, self.elapsed = '', (), 0, 0.0
        if previous and self.on_finish:
            self.on_finish(previous)

    def cancel(self) -> None:
        self.name, self.steps, self.index, self.elapsed = '', (), 0, 0.0
