"""Local-only relationship memory between monkey characters.

This stores only character indices and game events. It never observes the user's
computer, keyboard, files, or applications.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import tempfile

MAX_MONKEYS = 6


def _pair_key(a: int, b: int) -> str:
    if type(a) is not int or type(b) is not int or not (0 <= a < MAX_MONKEYS and 0 <= b < MAX_MONKEYS) or a == b:
        raise ValueError('relationship requires two different monkey indices from 0 to 5')
    lo, hi = sorted((a, b))
    return f'{lo}:{hi}'


class RelationshipStore:
    """Persistent relationship values in a small local JSON file."""
    def __init__(self, file: Path) -> None:
        self.file = Path(file)
        self.pairs: dict[str, dict[str, int]] = {}
        self.mentors: dict[str, int] = {}  # student index -> mentor index
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.file.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(raw, dict):
            return
        pairs = raw.get('pairs', {})
        if isinstance(pairs, dict):
            for key, values in pairs.items():
                try:
                    a, b = (int(part) for part in key.split(':'))
                    canonical = _pair_key(a, b)
                except (ValueError, TypeError, AttributeError):
                    continue
                if not isinstance(values, dict):
                    continue
                self.pairs[canonical] = {
                    'bond': self._bounded(values.get('bond'), -100, 100),
                    'rivalry': self._bounded(values.get('rivalry'), 0, 100),
                    'trust': self._bounded(values.get('trust'), 0, 100),
                    'interactions': self._bounded(values.get('interactions'), 0, 1_000_000),
                }
        mentors = raw.get('mentors', {})
        if isinstance(mentors, dict):
            for student, mentor in mentors.items():
                try:
                    s, m = int(student), int(mentor)
                except (ValueError, TypeError):
                    continue
                if 0 <= s < MAX_MONKEYS and 0 <= m < MAX_MONKEYS and s != m:
                    self.mentors[str(s)] = m

    @staticmethod
    def _bounded(value: object, low: int, high: int) -> int:
        if type(value) is not int:
            return 0
        return max(low, min(high, value))

    def get(self, a: int, b: int) -> dict[str, int | str]:
        key = _pair_key(a, b)
        values = self.pairs.get(key, {'bond': 0, 'rivalry': 0, 'trust': 0, 'interactions': 0})
        bond, rivalry, trust = values['bond'], values['rivalry'], values['trust']
        if rivalry >= 55:
            label = '死对头'
        elif bond <= -35:
            label = '互相嫌弃'
        elif bond >= 35 and trust >= 30:
            label = '好朋友'
        elif bond >= 18:
            label = '关系不错'
        else:
            label = '普通同事'
        return {**values, 'label': label}

    def _change(self, a: int, b: int, *, bond: int = 0, rivalry: int = 0,
                trust: int = 0) -> None:
        key = _pair_key(a, b)
        value = self.pairs.setdefault(key, {'bond': 0, 'rivalry': 0, 'trust': 0, 'interactions': 0})
        value['bond'] = max(-100, min(100, value['bond'] + bond))
        value['rivalry'] = max(0, min(100, value['rivalry'] + rivalry))
        value['trust'] = max(0, min(100, value['trust'] + trust))
        value['interactions'] = min(1_000_000, value['interactions'] + 1)
        self._save()

    def record_meeting(self, indices: list[int] | tuple[int, ...]) -> None:
        unique = sorted(set(i for i in indices if type(i) is int and 0 <= i < MAX_MONKEYS))
        for pos, a in enumerate(unique):
            for b in unique[pos + 1:]:
                self._change(a, b, bond=3, rivalry=-1, trust=2)

    def record_race(self, winner: int, loser: int) -> None:
        self._change(winner, loser, bond=-2, rivalry=5, trust=-1)

    def record_collision(self, a: int, b: int) -> None:
        self._change(a, b, bond=-1, rivalry=2)

    def record_shared_activity(self, a: int, b: int) -> None:
        self._change(a, b, bond=2, trust=1, rivalry=-1)

    def reconcile(self, a: int, b: int) -> None:
        self._change(a, b, bond=10, trust=8, rivalry=-8)

    def set_mentor(self, mentor: int, student: int) -> None:
        _pair_key(mentor, student)
        self.mentors[str(student)] = mentor
        self._save()

    def mentor_of(self, student: int) -> int | None:
        return self.mentors.get(str(student))

    def clear(self) -> None:
        self.pairs.clear()
        self.mentors.clear()
        try:
            self.file.unlink(missing_ok=True)
        except OSError:
            pass

    def _save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=self.file.parent, prefix='.relationships-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'version': 1, 'pairs': self.pairs, 'mentors': self.mentors},
                          handle, ensure_ascii=False, indent=2)
            os.replace(temp, self.file)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
