"""Local-only, explicitly opt-in monkey milestones without activity monitoring."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile

COUNTERS = ('taps', 'feeds', 'throws', 'stories', 'focus_sessions', 'focus_minutes')
BADGES: tuple[tuple[str, str, str, int], ...] = (
    ('first_feed', '🍌 香蕉初体验', 'feeds', 1),
    ('banana_king', '🍌 香蕉供应商', 'feeds', 10),
    ('tap_tap', '👉 研究对象', 'taps', 20),
    ('gravity', '🚀 牛顿的朋友', 'throws', 5),
    ('story', '🎭 事故亲历者', 'stories', 5),
    ('focus', '📚 正经教授', 'focus_sessions', 1),
    ('focus_120', '🏆 猴学博士', 'focus_minutes', 120),
)


@dataclass
class ProgressStore:
    file: Path
    enabled: bool = False

    def __post_init__(self) -> None:
        self.file = Path(self.file)
        self.counts = {key: 0 for key in COUNTERS}
        self._load()

    def _load(self) -> None:
        if not self.enabled:
            return
        try:
            raw = json.loads(self.file.read_text(encoding='utf-8'))
            if not isinstance(raw, dict):
                return
            self.counts.update({key: min(1000000, value) for key, value in raw.items()
                                if key in COUNTERS and type(value) is int and 0 <= value <= 1000000})
        except (OSError, ValueError, TypeError):
            return

    def enable(self) -> None:
        if not self.enabled:
            self.enabled = True
            self._load()

    def disable(self) -> None:
        self.enabled = False

    def unlocked(self) -> set[str]:
        return {key for key, _name, counter, target in BADGES if self.counts[counter] >= target}

    def record(self, kind: str, amount: int = 1) -> list[str]:
        if kind not in COUNTERS or type(amount) is not int or amount < 1 or amount > 180:
            raise ValueError('invalid progress event')
        if not self.enabled:
            return []
        before = self.unlocked()
        self.counts[kind] = min(1000000, self.counts[kind] + amount)
        self._save()
        return [name for key, name, _counter, _target in BADGES
                if key in self.unlocked() and key not in before]

    def _save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.file.parent, prefix='.progress-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(self.counts, handle, indent=2, ensure_ascii=False)
            os.replace(temporary, self.file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def clear(self) -> None:
        self.counts = {key: 0 for key in COUNTERS}
        try:
            self.file.unlink(missing_ok=True)
        except OSError:
            pass
