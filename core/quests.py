"""Small, local daily missions. No account, network, or activity monitoring."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import os
import tempfile

TASKS = {
    'feed': {'title': '🍌 喂一只猴子', 'description': '给任意一只猴子投喂香蕉', 'target': 1},
    'story': {'title': '🎭 看一场短剧', 'description': '手动开启一段猴学短剧', 'target': 1},
    'group': {'title': '🗳 召开猴学委员会', 'description': '需要至少两只猴子', 'target': 1, 'min_monkeys': 2},
    'race': {'title': '🏁 举办香蕉竞速', 'description': '放置公共香蕉，让猴子竞速', 'target': 1, 'min_monkeys': 2},
}


class QuestBoard:
    def __init__(self, file: Path, today: date | None = None) -> None:
        self.file = Path(file)
        self.today = (today or date.today()).isoformat()
        self.points = 0
        self.progress: dict[str, int] = {}
        self.reward_claimed = False
        self.completed_days = 0
        self._load()
        self._refresh_day(today or date.today())

    def _load(self) -> None:
        try:
            raw = json.loads(self.file.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(raw, dict):
            return
        self.points = self._safe_int(raw.get('points'), 0, 10_000_000)
        self.completed_days = self._safe_int(raw.get('completed_days'), 0, 1_000_000)
        raw_date = raw.get('date')
        if isinstance(raw_date, str):
            try:
                date.fromisoformat(raw_date)
                self.today = raw_date
            except ValueError:
                pass
        progress = raw.get('progress', {})
        if isinstance(progress, dict):
            self.progress = {k: self._safe_int(v, 0, 1000) for k, v in progress.items() if k in TASKS}
        self.reward_claimed = raw.get('reward_claimed') is True

    @staticmethod
    def _safe_int(value: object, low: int, high: int) -> int:
        return max(low, min(high, value)) if type(value) is int else low

    def _refresh_day(self, today: date) -> None:
        value = today.isoformat()
        if self.today != value:
            self.today = value
            self.progress = {}
            self.reward_claimed = False
            self._save()

    @property
    def active_ids(self) -> tuple[str, ...]:
        """Three rotating missions: feed + story + one colony mission."""
        day_number = int(self.today[-2:])
        third = 'group' if day_number % 2 else 'race'
        return ('feed', 'story', third)

    def record(self, event: str, amount: int = 1, *, today: date | None = None) -> bool:
        if today is not None:
            self._refresh_day(today)
        elif date.today().isoformat() != self.today:
            self._refresh_day(date.today())
        if event not in TASKS or type(amount) is not int or not 1 <= amount <= 100:
            return False
        if event not in self.active_ids:
            return False
        target = TASKS[event]['target']
        before = self.progress.get(event, 0)
        self.progress[event] = min(target, before + amount)
        completed = self._all_complete()
        if completed and not self.reward_claimed:
            self.points += 3
            self.completed_days += 1
            self.reward_claimed = True
        self._save()
        return self.progress[event] > before

    def _all_complete(self) -> bool:
        return all(self.progress.get(key, 0) >= TASKS[key]['target'] for key in self.active_ids)

    def snapshot(self, monkey_count: int = 1, *, today: date | None = None) -> dict:
        clock_day = today or date.today()
        if clock_day.isoformat() != self.today:
            self._refresh_day(clock_day)
        rows = []
        for key in self.active_ids:
            task = TASKS[key]
            progress = self.progress.get(key, 0)
            locked = monkey_count < task.get('min_monkeys', 1)
            rows.append({'id': key, **task, 'progress': progress, 'done': progress >= task['target'],
                         'locked': locked, 'display': f'{progress}/{task["target"]}'})
        return {'date': self.today, 'tasks': rows, 'points': self.points,
                'completed_days': self.completed_days, 'all_complete': self._all_complete(),
                'reward_claimed': self.reward_claimed, 'reward_points': 3}

    def clear(self) -> None:
        self.points = 0
        self.progress = {}
        self.reward_claimed = False
        self.completed_days = 0
        try:
            self.file.unlink(missing_ok=True)
        except OSError:
            pass

    def _save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=self.file.parent, prefix='.quests-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'version': 1, 'date': self.today, 'progress': self.progress,
                           'points': self.points, 'completed_days': self.completed_days,
                           'reward_claimed': self.reward_claimed}, handle, ensure_ascii=False, indent=2)
            os.replace(temp, self.file)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
