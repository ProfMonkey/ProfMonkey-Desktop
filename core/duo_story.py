"""Finite two-beat monkey encounters; pure Python, no desktop access.

An encounter is committed to relationship memory only when the second beat
finishes. Any drag, pause, focus session or hide may cancel it without effects.
"""
from __future__ import annotations
from dataclasses import dataclass
from core.encounters import Encounter


@dataclass(frozen=True)
class DuoBeat:
    seconds: float
    first: tuple[str, str]
    second: tuple[str, str]


OUTCOMES: dict[str, DuoBeat] = {
    'debate': DuoBeat(2.1, ('blink', '不吵了，先复现实验。'), ('idle', '那就把香蕉还给我。')),
    'high_five': DuoBeat(2.1, ('wake', '合作成功，记进猴山年鉴！'), ('blink', '这次终于没有爆炸。')),
    'nap': DuoBeat(2.1, ('sleep', '休息是一门严谨的学科。'), ('idle', '论文题目叫《闭眼的艺术》。')),
    'prank': DuoBeat(2.1, ('angry', '等等，香蕉真的会写代码？'), ('blink', '骗你的，但是 bug 是真的。')),
    'hello': DuoBeat(2.1, ('blink', '明天继续研究！'), ('wake', '好的，今天先吃香蕉。')),
    'invention': DuoBeat(2.1, ('fall', '实验装置怎么冒烟了？！'), ('blink', '我把“关闭”做成了“加速”！')),
    'inspection': DuoBeat(2.1, ('angry', '猴山纪律第九条：不要乱改规则！'), ('blink', '那我改第十条。')),
    'roll_call': DuoBeat(2.1, ('wake', '点名结束，少了一只猴。'), ('sleep', '我在梦里打过卡了。')),
    'boundary': DuoBeat(2.1, ('blink', '算了，这个玩笑到此为止。'), ('wake', '谢谢你，这次没有吓我。')),
    'library': DuoBeat(2.1, ('idle', '安静读书也算猴山贡献。'), ('blink', '嗯，这样刚刚好。')),
    'sleep_machine': DuoBeat(2.1, ('blink', '机器说你已经睡了十小时。'), ('sleep', '请问能再续费吗？')),
    'launch': DuoBeat(2.1, ('wake', '允许试飞，但禁止撞桌面。'), ('fall', '发射成功，降落方案忘写了！')),
}

# Role-addressed second beats avoid giving the captain's line to the sleepy
# monkey when their indices happen to be reversed.
ROLE_OUTCOMES: dict[str, dict[str, tuple[str, str]]] = {
    'invention': {
        'scholar': ('angry', '风险评估呢？这份报告还得重写。'),
        'inventor': ('fall', '看来安全按钮也需要安全按钮。')},
    'inspection': {
        'captain': ('angry', '不许再修改猴山宪章！'),
        'trickster': ('blink', '那我申请发布热修复补丁。')},
    'roll_call': {
        'captain': ('blink', '出勤率百分之百，清醒率待统计。'),
        'sleepy': ('sleep', '请替我签收一张请假条。')},
    'boundary': {
        'trickster': ('blink', '好，那我们改成安静实验。'),
        'shy': ('wake', '谢谢，这个我愿意参加。')},
    'library': {
        'scholar': ('idle', '这篇论文标题叫《沉默是猴》。'),
        'shy': ('blink', '终于找到一个不吵闹的角落。')},
    'sleep_machine': {
        'inventor': ('blink', '统计完毕：你的睡眠超过上限。'),
        'sleepy': ('sleep', '那就给上限升个级。')},
    'launch': {
        'captain': ('wake', '批准试飞，必须写清楚事故报告。'),
        'inventor': ('fall', '事故报告我已经预填好了！')},
}


class DuoStory:
    """One encounter, two finite beats, no timers or I/O of its own."""

    def __init__(self) -> None:
        self.event: Encounter | None = None
        self.index = 0
        self.elapsed = 0.0

    @property
    def active(self) -> bool:
        return self.event is not None

    @property
    def beat(self) -> DuoBeat | None:
        if self.event is None:
            return None
        if self.index == 0:
            e = self.event
            return DuoBeat(2.4, (e.action_first, e.line_first),
                           (e.action_second, e.line_second))
        role_outcomes = ROLE_OUTCOMES.get(self.event.kind)
        if role_outcomes:
            fallback = ('blink', '猴山又有新发现。')
            return DuoBeat(2.1,
                           role_outcomes.get(self.event.personality_first, fallback),
                           role_outcomes.get(self.event.personality_second, fallback))
        return OUTCOMES.get(self.event.kind, OUTCOMES['hello'])

    def start(self, event: Encounter) -> bool:
        if self.active:
            return False
        self.event = event
        self.index = 0
        self.elapsed = 0.0
        return True

    def advance(self, dt: float) -> bool:
        """Return True if the beat changes or the encounter finishes.

        Event stays available until the caller commits its consequences and
        calls cancel(). Interrupting must not commit any relationship change.
        """
        if not 0 <= dt <= .5:
            raise ValueError('invalid duo-story delta')
        if not self.active or self.finished:
            return False
        self.elapsed += dt
        if self.elapsed < self.beat.seconds:
            return False
        self.elapsed -= self.beat.seconds
        self.index += 1
        return True

    @property
    def finished(self) -> bool:
        return self.active and self.index >= 2

    def cancel(self) -> None:
        self.event = None
        self.index = 0
        self.elapsed = 0.0
