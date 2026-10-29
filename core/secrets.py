"""ProfMonkey v0.21: six *hidden* investigations and non-intrusive easter eggs.

All events are fictional. Player gestures only count after actual pet UI actions:
feeding, a 4-click streak, completing a public banana race, touching a mirror.
No OS telemetry, timers, screenshot, clipboard, keyboard or web access.

Each case has 3 chapters x 3 desktop beats x 2 choices (36 branch-aware story
variants, 54 fixed scene slots). Case/gesture history is one bounded local
journal, committed only after the *entire* on-screen chapter ends.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import tempfile
from pathlib import Path
from core.profiles import clean_profiles, PERSONALITIES

# Six protagonist personalities, all newly redesigned in v0.20.
# Each chapter: title, suspicious discovery, specific follow-up evidence.
SECRET_CASES = {
 'banana_receipt': {
    'title': '🍌 消失的第七张收据', 'lead': 'trickster',
    'hint': '给猴子投喂香蕉至少3次。',
    'chapters': (
      ('第一章 · 仓库里的空白账单', '香蕉库房清点后，出现一张没有购买人的收据。', '纸背面竟有干饭猴自己的签名，笔迹却是反过来的。'),
      ('第二章 · 永远少一根', '不管仓库怎么补货，账本总比实物多一根香蕉。', '失踪的不是香蕉，是一张被用作书签的旧收据。'),
      ('第三章 · 记账的真凶', '监控只拍到了一个背影：它手里拿着一本书。', '教授猴用收据夹书签，干饭猴却拿它写了一张假欠条。'),
    ),
    'truth': '公开账本后全城发现：真正被偷走的是大家对数字的信任。',
    'secret': '干饭猴悄悄归还了书签，却把“香蕉税”写进下一本空白账册。',
 },
 'shadow_07': {
    'title': '👤 第七道猴影', 'lead': 'shy',
    'hint': '同时养6只猴子，并点过一次桌面镜子。',
    'chapters': (
      ('第一章 · 六只猴子，七个影子', '酷帅猴整理舞台，发现墙上多出一条尾巴。', '多出的尾巴只在镜子被搬到广场后出现。'),
      ('第二章 · 没有脚印的住客', '队长逐一核对六只猴子的鞋印，竟然全部对得上。', '“第七只”从来没有落过地，它每次都在角色抬手时行动。'),
      ('第三章 · 镜中未署名者', '镜子里，一个影子迟了半拍才向大家挥手。', '那不是第七只动物，而是有人偷偷做的纸板影戏；可是最后一张纸板自己动了一下。'),
    ),
    'truth': '影戏的道具被公开，所有猴子都笑了；最后那半拍没人能解释。',
    'secret': '酷帅猴把纸板收起，却发现背面写着下一场演出的日期：明天。',
 },
 'signal_404': {
    'title': '📡 银河发来404', 'lead': 'scholar',
    'hint': '建造银河观测台，并完成至少1章银河信号原案。',
    'chapters': (
      ('第一章 · 收不到的第404号信号', '观测台捕获一串不断重复的数字：404。', '校准后才知道，信号在提醒大家“这条消息不在这里”。'),
      ('第二章 · 天空中的错别字', '星图指向一颗不存在的星，名字却像一段猴山笑话。', '发射时间恰好等于猴山第一次记录香蕉事故的时刻。'),
      ('第三章 · 最后一条回信', '科学组按原路回发信号，接收屏出现一句话。', '“你们一直在寻找宇宙，为什么没有看看自己写下的第一行代码？”'),
    ),
    'truth': '旧实验日志曝光：银河噪声来自观测台的回声程序；但程序没有回信功能。',
    'secret': '教授关闭了程序，屏幕仍短暂显示“下一位观测者已上线”。',
 },
 'sleep_strike': {
    'title': '💤 猴山睡眠总罢工', 'lead': 'sleepy',
    'hint': '连续快速点一只猴子4下，累计触发2次。',
    'chapters': (
      ('第一章 · 史上最长的五分钟', '摸鱼猴宣布午睡五分钟。六小时后，它仍在计时第一分钟。', '编程猴检查时钟，发现秒针被贴成了香蕉形状。'),
      ('第二章 · 失踪的闹钟', '全猴山的闹钟都变成了助眠音乐播放器。', '最早一个闹钟被干饭猴设置成“响铃后自动申请假条”。'),
      ('第三章 · 睡眠革命的结局', '探险猴拿着出勤表来到广场，发现所有名字都已经签好了。', '原来摸鱼猴在梦里开过一次会议，还留下了完整会议纪要。'),
    ),
    'truth': '会议纪要被公开：决定每只猴子都有午休权，闹钟恢复正常。',
    'secret': '摸鱼猴把会议纪要藏进枕头，明天的出勤表上又多出一枚“已休息”的章。',
 },
 'button_zero': {
    'title': '🧪 实验室的零号按钮', 'lead': 'inventor',
    'hint': '建成联合实验室，并完成它的原案至少1章。',
    'chapters': (
      ('第一章 · 谁装了不存在的按钮', '实验台只有1到9号按钮，突然多出一个0号。', '没人记得安装过它，说明书却写着“禁止直接按下”。'),
      ('第二章 · 凭空多出来的试管', '队长安排封锁现场，试管架第二天仍多了一支。', '每按一次0号，装置就把一个丢失的实验假设打印出来。'),
      ('第三章 · 0的真正用途', '编程猴终于读懂底部刻字：REWIND ONE QUESTION。', '按钮不会让时间倒流，它只会让参与者重新回答当初没敢说出口的问题。'),
    ),
    'truth': '实验室公开零号按钮的用途：失败不是事故，逃避才是。设备正式封存。',
    'secret': '按钮被锁进箱子。凌晨箱内却传出一声“还剩一次机会”。',
 },
 'last_ballot': {
    'title': '🗳️ 最后一张反对票', 'lead': 'captain',
    'hint': '完成文明演化中的共同宪章，并至少养3只猴子。',
    'chapters': (
      ('第一章 · 投票箱里没人认领的票', '议会结束后，工作人员发现多出一张没有署名的反对票。', '纸张来自一份很久以前就废除的香蕉分配规定。'),
      ('第二章 · 不存在的选民', '队长查遍名单，票数与签到人数总是差一。', '那张票不是哪个猴子投的，是一封请求未来重新审议的申请。'),
      ('第三章 · 给未来的留言', '队长终于找到折在票里的第二张纸条。', '“如果有一天所有猴子都同意，请替最后一个不敢开口的猴子留下位置。”'),
    ),
    'truth': '议会公开保留匿名意见席，城市决定让未来的不同声音也能被听见。',
    'secret': '队长将纸条秘密归档。隔天投票箱里出现第二张：“谢谢你听到了。”',
 },
}
ROUTES = ('reveal', 'hide')
ROUTE_NAMES = {'reveal': '🔦 公开线索', 'hide': '🌙 悄悄保存'}
GESTURES = {'feed': 'feeds', 'rapid_tap': 'rapid_taps',
            'race': 'races', 'mirror': 'mirrors'}
LIMITS = {'feeds': 3, 'rapid_taps': 2, 'races': 1, 'mirrors': 1}
MAX_NEWS = 36
# Extra phrases vary with the actor's current user-chosen personality.
PERSONA_REACTIONS = {
 'scholar': ('这份证据必须公开复核。', '先把它放进没有署名的档案。'),
 'trickster': ('公开吧！反正被怀疑的总是我。', '嘘，这个彩蛋先留给下一只猴子。'),
 'sleepy': ('宣布完能不能让我睡？', '悄悄睡一觉，明天再看。'),
 'inventor': ('我要把结论写进实验日志。', '先做一台不会泄密的保险柜。'),
 'captain': ('全员见证，按流程登记。', '探险猴保证暂时不声张。'),
 'shy': ('我愿意把发现告诉大家。', '能不能给我一点时间整理心情？'),
}


@dataclass(frozen=True)
class SecretBeat:
    seconds: float
    poses: tuple[tuple[int, str, str], ...]


@dataclass(frozen=True)
class SecretPlan:
    case_id: str
    chapter: int
    first: int
    second: int
    route: str
    expected: tuple[int, int, int]
    ending: str
    beats: tuple[SecretBeat, ...]


def _row():
    return {'chapter': 0, 'reveal': 0, 'hide': 0, 'ending': ''}


def _clean_progress(value: object) -> dict:
    if not isinstance(value, dict):
        return _row()
    a,b,c=value.get('chapter'),value.get('reveal'),value.get('hide')
    e=value.get('ending','')
    if (type(a) is int and 0<=a<=3 and type(b) is int and type(c) is int
        and 0<=b<=3 and 0<=c<=3 and b+c==a and type(e) is str
        and e in ('','unmasked','unresolved') and (a==3)==(e!='')):
        return {'chapter':a,'reveal':b,'hide':c,'ending':e}
    return _row()


class SecretJournal:
    """Local-only story receipts. No file created merely by browsing a menu."""
    def __init__(self,path:Path):
        self.path=Path(path)
        self.gestures={k:0 for k in LIMITS}
        self.cases={k:_row() for k in SECRET_CASES}
        self.news:list[dict]=[]
        self._load()

    def _load(self):
        try:
            raw=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            return
        if not isinstance(raw,dict) or raw.get('version')!=1:
            return
        gestures=raw.get('gestures')
        if isinstance(gestures,dict):
            for key,limit in LIMITS.items():
                val=gestures.get(key)
                if type(val) is int and 0<=val<=limit:
                    self.gestures[key]=val
        cases=raw.get('cases')
        if isinstance(cases,dict):
            for key in SECRET_CASES:
                self.cases[key]=_clean_progress(cases.get(key))
        news=raw.get('news')
        if isinstance(news,list):
            for row in news[-MAX_NEWS:]:
                if not isinstance(row,dict): continue
                key,chapter,route=row.get('case'),row.get('chapter'),row.get('route')
                if (type(key) is str and key in SECRET_CASES and type(chapter) is int
                        and 1<=chapter<=3 and type(route) is str and route in ROUTES):
                    self.news.append({'case':key,'chapter':chapter,'route':route})

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix='.secrets-',suffix='.json',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                json.dump({'version':1,'gestures':self.gestures,'cases':self.cases,
                           'news':self.news},stream,ensure_ascii=False,indent=2)
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def observe_gesture(self,gesture:str)->bool:
        """The True result is one-time and can be displayed as subtle speech."""
        if type(gesture) is not str or gesture not in GESTURES:
            return False
        key=GESTURES[gesture]
        old=self.gestures[key]
        if old>=LIMITS[key]:
            return False
        self.gestures[key]=old+1
        try:
            self._save()
        except OSError:
            self.gestures[key]=old
            return False
        return self.gestures[key]==LIMITS[key]

    def cleared(self,case_id:str)->bool:
        return self.cases[case_id]['chapter']==3

    def unlocked(self,case_id:str, count:int, profiles:list[dict],
                 expeditions=None) -> tuple[bool,str]:
        if case_id not in SECRET_CASES or type(count) is not int or not 2<=count<=6:
            return False,'需要至少两只猴子。'
        story=SECRET_CASES[case_id]
        people=clean_profiles(profiles)[:count]
        if not any(p['personality']==story['lead'] for p in people):
            return False,'当前猴山尚没有对应的主角：'+PERSONALITIES[story['lead']]
        structures=getattr(expeditions,'buildings',frozenset())
        city_cases=getattr(expeditions,'city_cases',{})
        if case_id=='banana_receipt' and self.gestures['feeds']<3:
            return False,story['hint']
        if case_id=='shadow_07' and (count!=6 or self.gestures['mirrors']<1):
            return False,story['hint']
        if case_id=='signal_404' and (
            'galaxy_scope' not in structures or city_cases.get('galaxy_scope',{}).get('chapter',0)<1):
            return False,story['hint']
        if case_id=='sleep_strike' and self.gestures['rapid_taps']<2:
            return False,story['hint']
        if case_id=='button_zero' and (
            'monkey_academy' not in structures or
            city_cases.get('monkey_academy',{}).get('chapter',0)<1):
            return False,story['hint']
        if case_id=='last_ballot':
            history=getattr(expeditions,'legacy_events',[])
            if count<3 or not any(
                isinstance(row,dict) and row.get('event')=='constitution'
                for row in history
            ):
                return False,story['hint']
        return True,'🗝️ 已发现隐藏线索！'

    def record(self,plan:SecretPlan,count:int,profiles:list[dict],expeditions=None)->bool:
        """Only one unmodified full chapter may advance, after stage 3 plays."""
        if not isinstance(plan,SecretPlan):return False
        try:
            expected=prepare_secret(self,plan.case_id,plan.first,plan.second,
                                    plan.route,count,profiles,expeditions)
        except (ValueError,KeyError):
            return False
        if plan!=expected:return False
        previous=dict(self.cases[plan.case_id])
        old_news=list(self.news)
        row=self.cases[plan.case_id]
        row['chapter']+=1
        row[plan.route]+=1
        row['ending']=plan.ending if row['chapter']==3 else ''
        self.news=(self.news+[{'case':plan.case_id,'chapter':row['chapter'],
                               'route':plan.route}])[-MAX_NEWS:]
        try:
            self._save()
        except OSError:
            self.cases[plan.case_id]=previous
            self.news=old_news
            return False
        return True

    def epilogue(self) -> str | None:
        """Final in-world easter egg unlocked by completing all six stories.

        This is narrative only: there is no seventh pet, paid DLC, or extra
        resource claim. The final text respects the 6 branch outcomes.
        """
        if any(self.cases[key]['chapter']!=3 for key in SECRET_CASES):
            return None
        revealed=sum(row['ending']=='unmasked' for row in self.cases.values())
        if revealed>=4:
            return ('🌠 隐藏终章：六份案卷背面拼成一行字——'
                    '“第七位见证者，一直坐在屏幕外。”'
                    '六只猴子同时抬头。它们发现，真正记录猴山历史的是你。')
        return ('🌑 隐藏终章：六份保密档案的封口印，'
                '拼成了一个还没出现的脚印。'
                '队长锁上档案柜，柜子里却传出一声轻轻的“谢谢”。')

    def clear(self):
        old=(dict(self.gestures),{k:dict(v) for k,v in self.cases.items()},
             list(self.news))
        self.gestures={k:0 for k in LIMITS}
        self.cases={k:_row() for k in SECRET_CASES}
        self.news=[]
        try:
            self._save()
        except OSError:
            self.gestures,self.cases,self.news=old
            raise


def prepare_secret(journal:SecretJournal,case_id:str,first:int,second:int,
                   route:str,count:int,profiles:list[dict],
                   expeditions=None)->SecretPlan:
    """Immutable, verified 3-beat episode with a real mystery and reveal."""
    if type(case_id) is not str or case_id not in SECRET_CASES:
        raise ValueError('unknown hidden storyline')
    if type(route) is not str or route not in ROUTES:
        raise ValueError('invalid hidden storyline route')
    if (type(count) is not int or not 2<=count<=6 or
        type(first) is not int or type(second) is not int or
        not 0<=first<count or not 0<=second<count or first==second):
        raise ValueError('select two different visible monkeys')
    unlocked,reason=journal.unlocked(case_id,count,profiles,expeditions)
    if not unlocked:raise ValueError(reason)
    people=clean_profiles(profiles)
    story=SECRET_CASES[case_id]
    if people[first]['personality']!=story['lead']:
        raise ValueError('the first performer must be the indicated protagonist')
    row=journal.cases[case_id]
    stage=row['chapter']
    if stage>=3:raise ValueError('this hidden case is already fully completed')
    title,opening,evidence=story['chapters'][stage]
    public=route=='reveal'
    a=people[first]['name'];b=people[second]['name']
    tone='公开这条线索' if public else '暂时收好线索'
    response=PERSONA_REACTIONS[people[second]['personality']][0 if public else 1]
    final=(stage==2)
    # A case has two replay-safe endings based on the *entire* sequence, not
    # just the last click. One current route cannot erase older chapters.
    reveals=row['reveal']+int(public)
    hides=row['hide']+int(not public)
    ending=('unmasked' if reveals>=2 else 'unresolved') if final else ''
    if final:
        close=story['truth'] if ending=='unmasked' else story['secret']
    else:
        close=('线索已公开，新的证人决定在下一章开口。' if public
               else '线索暂时保密，但第二天又出现一条新痕迹。')
    beats=(
        SecretBeat(2.1,((first,'wake',title+'！'),
                        (second,'blink',opening))),
        SecretBeat(2.6,((first,'angry' if not public else 'walk',
                         evidence+' '+tone+'。'),
                        (second,'blink',b+'：'+response))),
        SecretBeat(2.5,((first,'idle',close),
                        (second,'wake' if ending!='unresolved' else 'angry',
                         ('案卷已结。' if final else '下次还要接着调查。')+
                         ' 🐒 '+a+'和'+b+'不会忘记这次选择。'))),
    )
    return SecretPlan(case_id,stage,first,second,route,
                      (stage,row['reveal'],row['hide']),ending,beats)


class SecretStory:
    """Exactly three visible beats before an irreversible local save."""
    def __init__(self):
        self.plan:SecretPlan|None=None
        self.index=0
        self.elapsed=0.
        self._consumed=False

    @property
    def active(self):return self.plan is not None

    @property
    def finished(self):return self.active and self.index>=len(self.plan.beats)

    @property
    def beat(self):
        return self.plan.beats[self.index] if self.active and not self.finished else None

    def start(self,plan:SecretPlan)->bool:
        if self.active or not isinstance(plan,SecretPlan) or len(plan.beats)!=3:
            return False
        self.plan,self.index,self.elapsed,self._consumed=plan,0,0.,False
        return True

    def advance(self,seconds:float)->bool:
        if type(seconds) not in (int,float) or not 0<=seconds<=.5:
            raise ValueError('invalid secret story timestep')
        if not self.active or self.finished:return False
        self.elapsed+=seconds
        if self.elapsed<self.beat.seconds:return False
        self.elapsed-=self.beat.seconds
        self.index+=1
        return True

    def consume_completion(self)->bool:
        if not self.finished or self._consumed:return False
        self._consumed=True
        return True

    def cancel(self):
        self.plan,self.index,self.elapsed,self._consumed=None,0,0.,False
