"""In-universe governance from finished monkey votes; no real OS policies.

A policy changes only local *fictional* monkey actions. The store never reads
desktop content, tracks the user or alters the host system's audio permissions.
Only completed, explicitly initiated councils may call enact().
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile

POLICIES = {
    'banana_rules': ('🍌 香蕉共享条例',
                     '公共香蕉竞速仍然进行；赢家分给其他猴子一小块，关系由竞争改为合作。'),
    'quiet_hours': ('🌙 猴山安静公约',
                    '暂停自动开始的猴山群演和随机双猴偶遇；手动互动仍可正常开启。'),
    'rocket_license': ('🚀 火箭试飞许可',
                       '允许用户手动启动发明猴的虚构三幕试飞剧情，不影响真实电脑。'),
}
OUTCOMES = ('adopted', 'rejected', 'stalemate')
MAX_HISTORY = 24


class MonkeyLaws:
    """Safe, bounded and separately erasable rulebook for monkey fiction."""

    def __init__(self, file: Path) -> None:
        self.file = Path(file)
        self.states: dict[str, bool] = {key: False for key in POLICIES}
        self.history: list[dict[str, str | bool]] = []
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.file.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(raw, dict) or raw.get('version') != 1:
            return
        states = raw.get('states')
        if isinstance(states, dict):
            for key in POLICIES:
                if type(states.get(key)) is bool:
                    self.states[key] = states[key]
        history = raw.get('history')
        if isinstance(history, list):
            for record in history[-MAX_HISTORY:]:
                if not isinstance(record, dict):
                    continue
                key, outcome, active = (record.get('issue'), record.get('outcome'),
                                        record.get('active'))
                if type(key) is str and key in POLICIES and type(outcome) is str and outcome in OUTCOMES and type(active) is bool:
                    self.history.append({'issue': key, 'outcome': outcome, 'active': active})

    def _save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(dir=self.file.parent, prefix='.monkey-laws-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'states': self.states, 'history': self.history},
                          stream, ensure_ascii=False, indent=2)
            os.replace(path, self.file)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def active(self, issue: str) -> bool:
        """Unknown policies are never granted any privilege."""
        return bool(self.states.get(issue, False)) if type(issue) is str and issue in POLICIES else False

    def enact(self, issue: str, outcome: str) -> bool:
        """Enact only a completed ballot's *validated outcome*, not a preview.

        Returned True means this vote was recorded, even if tied and the state
        remains unchanged. Whoever calls this must enforce finished-once.
        """
        if type(issue) is not str or type(outcome) is not str or issue not in POLICIES or outcome not in OUTCOMES:
            return False
        if outcome == 'adopted':
            self.states[issue] = True
        elif outcome == 'rejected':
            self.states[issue] = False
        self.history.append({'issue': issue, 'outcome': outcome,
                             'active': self.states[issue]})
        self.history = self.history[-MAX_HISTORY:]
        self._save()
        return True

    def clear(self) -> None:
        """Forget monkey laws, without deleting monkey relationship history."""
        self.states = {key: False for key in POLICIES}
        self.history = []
        try:
            self.file.unlink(missing_ok=True)
        except OSError:
            pass
