"""Optional event bookmarks saved locally, no screenshots or sensitive metadata."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json


class History:
    def __init__(self, file: Path, enabled: bool = False) -> None:
        self.file, self.enabled = Path(file), enabled
        self.entries: list[dict[str, str]] = []
        if enabled:
            try:
                val = json.loads(self.file.read_text(encoding='utf-8'))
                if isinstance(val, list):
                    self.entries = [x for x in val[-100:] if isinstance(x, dict) and 'event' in x]
            except (OSError, ValueError, TypeError):
                pass

    def add(self, event: str) -> None:
        if not self.enabled:
            return
        self.entries.append({'event': event[:40], 'at': datetime.now(timezone.utc).isoformat()})
        self.entries = self.entries[-100:]
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding='utf-8')

    def clear(self) -> None:
        self.entries.clear()
        try:
            self.file.unlink(missing_ok=True)
        except OSError:
            pass
