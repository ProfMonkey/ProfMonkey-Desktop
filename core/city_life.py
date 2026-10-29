"""Four complete, branching fictional city cases, manually played in 3-act episodes.

All names, dialogue and rewards are fictional. The scene engine never scans
the desktop, runs shell commands, listens to the user or schedules itself.
Each chapter can be completed only once, with cancellation leaving no effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from core.civilization import BUILDINGS

CASE_TITLES = {
    'banana_vault': '🍌 午夜香蕉失窃案',
    'galaxy_scope': '🔭 来自银河深处的信号',
    'public_square': '🎉 猴山广场庆典',
    'monkey_academy': '🧪 联合实验室事故',
}
CASE_CHAPTERS = {
    'banana_vault': (
        ('第一章 · 空空的仓库', '巡逻猴发现香蕉仓库的账本不对劲。', '仓库门口出现一串可疑的香蕉皮脚印。'),
        ('第二章 · 失踪的收据', '一张奇怪的收据把大家引向老广场。', '究竟是有人偷吃，还是库存统计错误？'),
        ('第三章 · 猴山公开听证', '失窃案的证据终于被送到猴山议事桌上。', '一份新的仓储协议成为争论的焦点。'),
    ),
    'galaxy_scope': (
        ('第一章 · 会眨眼的星星', '银河望远镜突然收到一串奇怪的数字。', '一只猴子坚持那是外星香蕉价格表。'),
        ('第二章 · 反向观测', '信号居然随着猴子们转动镜筒而变化。', '地面上的某个物件可能干扰了观测。'),
        ('第三章 · 第一张星图', '猴子们决定公布自己的第一张星图。', '远处的一点微光成为了新的谜团。'),
    ),
    'public_square': (
        ('第一章 · 庆典准备日', '公共广场宣布举办第一届猴山文明庆典。', '海报上却忘记写谁来负责香蕉。'),
        ('第二章 · 彩排事故', '庆典队伍排错了方向，所有猴子撞在一起。', '是否要优先保证安全，还是继续追求效果？'),
        ('第三章 · 共同的舞台', '六只猴子终于站上了属于自己的舞台。', '即使是爱独处的猴子也有自己的位置。'),
    ),
    'monkey_academy': (
        ('第一章 · 烟雾报警', '联合实验室内突然冒出一团紫色烟雾。', '编程猴表示：实验本来就是紫色的。'),
        ('第二章 · 失控的机器', '一台香蕉驱动的机器居然开始自己做论文。', '教授猴要求先查实验记录再发布结果。'),
        ('第三章 · 新的实验室章程', '修好实验台后，大家讨论未来的科研规范。', '错误可以被承认，也能成为新发现的开始。'),
    ),
}
CASE_CHOICES = {
    'banana_vault': ('🔎 公开核对证据', '🐒 大胆追查嫌疑猴'),
    'galaxy_scope': ('📐 严格校准设备', '🚀 大胆追踪信号'),
    'public_square': ('🦺 优先照顾所有人', '🎆 追加震撼特效'),
    'monkey_academy': ('🧯 先完成安全检查', '⚡ 立即进行新实验'),
}
# Banana/science/reputation change per *completed chapter*. Each route has
# tradeoffs; negative balances are clamped to zero by the journal.
CASE_EFFECTS = {
    'banana_vault': {'careful': (-1, 0, 2), 'bold': (1, 0, -1)},
    'galaxy_scope': {'careful': (0, 2, 1), 'bold': (0, 3, -1)},
    'public_square': {'careful': (-1, 0, 2), 'bold': (-2, 0, 4)},
    'monkey_academy': {'careful': (0, -1, 2), 'bold': (0, 3, -2)},
}
MAX_CASE_NEWS = 24
PERSONA_REPLIES = {
    'scholar': ('我们先把证据链整理清楚。', '理论可以先不完美，实验必须做！'),
    'trickster': ('查案先从香蕉皮开始，嘿嘿。', '我有个大胆计划，保证很有趣！'),
    'sleepy': ('先查完案，再让我睡一会儿。', '边打盹边冒险也是本事。'),
    'inventor': ('我用自己做的工具检验一下。', '我保证这台机器不会再爆炸！'),
    'captain': ('全员注意安全，按计划行动。', '听我口令，现在开始行动！'),
    'shy': ('让我在角落里核对材料吧。', '我也想试一次新的办法……'),
}


@dataclass(frozen=True)
class LivingBeat:
    seconds: float
    poses: tuple[tuple[int, str, str], ...]


@dataclass(frozen=True)
class CityPlan:
    case_id: str
    chapter: int
    first: int
    second: int
    choice: str
    expected_state: tuple[int, int, int]  # completed chapters, careful, bold
    resource_delta: tuple[int, int, int]
    ending: str | None  # 'reconciled' or 'chaos' for final chapter
    beats: tuple[LivingBeat, ...]


def empty_case() -> dict[str, object]:
    return {'chapter': 0, 'careful': 0, 'bold': 0, 'ending': ''}


def normalize_cases(raw: object, buildings: frozenset[str]) -> dict[str, dict]:
    """Legacy v0.16 saves have no cases; malformed progress grants nothing."""
    result = {key: empty_case() for key in CASE_TITLES}
    if not isinstance(raw, dict):
        return result
    for key in CASE_TITLES:
        if key not in buildings:
            continue
        row = raw.get(key)
        if not isinstance(row, dict):
            continue
        stage = row.get('chapter')
        careful, bold = row.get('careful'), row.get('bold')
        ending = row.get('ending', '')
        if (type(stage) is int and 0 <= stage <= 3 and
                type(careful) is int and type(bold) is int and
                0 <= careful <= 3 and 0 <= bold <= 3 and
                careful + bold == stage and type(ending) is str and
                ending in ('', 'reconciled', 'chaos') and
                (stage == 3) == (ending != '')):
            result[key] = {'chapter': stage, 'careful': careful,
                           'bold': bold, 'ending': ending}
    return result


def case_delta(case_id: str, choice: str) -> tuple[int, int, int]:
    if (type(case_id) is not str or case_id not in CASE_TITLES or
            type(choice) is not str or choice not in ('careful', 'bold')):
        raise ValueError('invalid fictional case choice')
    return CASE_EFFECTS[case_id][choice]


def prepare_city_case(case_id: str, state: dict[str, object],
                      first: int, second: int, choice: str,
                      *, bond: int = 0, trust: int = 0,
                      first_personality: str | None = None,
                      second_personality: str | None = None) -> CityPlan:
    """Deterministic planned scene. The journal separately verifies progress."""
    if type(case_id) is not str or case_id not in CASE_TITLES:
        raise ValueError('unknown city case')
    if (type(first) is not int or type(second) is not int or
            not 0 <= first < 6 or not 0 <= second < 6 or first == second):
        raise ValueError('two distinct visible characters required')
    delta = case_delta(case_id, choice)
    stage, careful, bold = (state.get('chapter'), state.get('careful'), state.get('bold'))
    if (type(stage) is not int or not 0 <= stage < 3 or
            type(careful) is not int or type(bold) is not int or
            careful < 0 or bold < 0 or careful + bold != stage):
        raise ValueError('invalid or already finished case')
    title, start, clue = CASE_CHAPTERS[case_id][stage]
    careful_total = careful + (choice == 'careful')
    bold_total = bold + (choice == 'bold')
    ending = None
    if stage == 2:
        ending = ('reconciled' if careful_total >= 2 or
                  (careful_total >= 1 and bond >= 35 and trust >= 30)
                  else 'chaos')
    choice_text = CASE_CHOICES[case_id][0 if choice == 'careful' else 1]
    preferred = 0 if choice == 'careful' else 1
    first_reply = (PERSONA_REPLIES[first_personality][preferred]
                   if first_personality in PERSONA_REPLIES
                   else ('我找到了一条线索！' if choice == 'careful'
                         else '先大胆行动，别让谜题逃走！'))
    second_reply = (PERSONA_REPLIES[second_personality][preferred]
                    if second_personality in PERSONA_REPLIES
                    else clue)
    conclusion = (
        '大家达成共识，猴山迎来了新的篇章！' if ending == 'reconciled' else
        '问题依然存在，猴山还需要更多理解。' if ending == 'chaos' else
        '线索已经收进档案，下一章需要大家继续调查。'
    )
    beats = (
        LivingBeat(1.7, ((first, 'wake', title + '！'),
                         (second, 'blink', start))),
        LivingBeat(2.1, ((first, 'walk', first_reply),
                         (second, 'angry' if choice == 'bold' else 'blink',
                          clue + ' ' + second_reply + ' ' + choice_text))),
        LivingBeat(2.0, ((first, 'idle', conclusion),
                         (second, 'wake' if ending != 'chaos' else 'angry',
                          '这次选择已经写入猴山历史。'))),
    )
    return CityPlan(case_id, stage, first, second, choice,
                    (stage, careful, bold), delta, ending, beats)


class CityLifeStory:
    """Only a fully completed, unconsumed episode may be committed."""
    def __init__(self):
        self.plan: CityPlan | None = None
        self.index = 0
        self.elapsed = 0.
        self._consumed = False

    @property
    def active(self) -> bool:
        return self.plan is not None

    @property
    def finished(self) -> bool:
        return self.active and self.index >= len(self.plan.beats)

    @property
    def beat(self) -> LivingBeat | None:
        return self.plan.beats[self.index] if self.active and not self.finished else None

    def start(self, plan: CityPlan) -> bool:
        if self.active or not isinstance(plan, CityPlan):
            return False
        if (plan.case_id not in CASE_TITLES or len(plan.beats) != 3 or
                not 0 <= plan.chapter < 3):
            return False
        self.plan, self.index, self.elapsed, self._consumed = plan, 0, 0., False
        return True

    def advance(self, dt: float) -> bool:
        if type(dt) not in (int, float) or not 0 <= dt <= .5:
            raise ValueError('invalid story delta')
        if not self.active or self.finished:
            return False
        self.elapsed += dt
        if self.elapsed < self.beat.seconds:
            return False
        self.elapsed -= self.beat.seconds
        self.index += 1
        return True

    def consume_completion(self) -> bool:
        if not self.finished or self._consumed:
            return False
        self._consumed = True
        return True

    def cancel(self) -> None:
        self.plan, self.index, self.elapsed, self._consumed = None, 0, 0., False
