"""Conservative, validated, offline JSON settings with atomic writes."""
from __future__ import annotations
from dataclasses import dataclass, asdict, fields, field
from pathlib import Path
import json
import os
import tempfile


@dataclass
class Settings:
    mode: str = 'QUIET'
    size: int = 160
    monkey_count: int = 1  # one real independent window per monkey, up to six
    monkey_profiles: list[dict[str, str]] = field(default_factory=list)
    social_enabled: bool = False  # autonomous group skits are opt-in and monkey-mode only
    colony_behavior: str = 'free'  # free / follow; followers can track the professor
    collisions_enabled: bool = True  # soft sprite-to-sprite cartoon collisions
    ambient_encounters: bool = False  # opt-in autonomous two-monkey micro-stories
    sound: bool = False
    always_on_top: bool = True
    stories: bool = True
    history: bool = False
    skin: str = 'professor'
    quiet_interval: int = 600
    monkey_interval: int = 240
    input_tracking: bool = False  # reserved: not implemented, never a keylogger
    progress_enabled: bool = False  # opt-in local-only achievements
    custom_quotes: list[str] = field(default_factory=list)

    def validated(self) -> 'Settings':
        self.mode = self.mode if self.mode in ('QUIET', 'MONKEY') else 'QUIET'
        self.size = min(240, max(90, int(self.size)))
        from core.colony import clamp_count
        self.monkey_count = clamp_count(self.monkey_count)
        from core.profiles import clean_profiles
        self.monkey_profiles = clean_profiles(self.monkey_profiles)
        self.skin = self.skin if self.skin in ('professor', 'night', 'suit', 'exam') else 'professor'
        self.colony_behavior = self.colony_behavior if self.colony_behavior in ('free', 'follow') else 'free'
        self.quiet_interval = max(90, min(3600, int(self.quiet_interval)))
        self.monkey_interval = max(40, min(1800, int(self.monkey_interval)))
        for attr in ('sound', 'always_on_top', 'stories', 'history', 'progress_enabled', 'social_enabled', 'collisions_enabled', 'ambient_encounters'):
            setattr(self, attr, bool(getattr(self, attr)))
        # No system-wide input watcher in this build; prohibit enabling it silently.
        quotes = self.custom_quotes if isinstance(self.custom_quotes, list) else []
        cleaned = []
        for quote in quotes:
            if isinstance(quote, str):
                trimmed = "".join(c for c in quote if c.isprintable()).strip()[:44]
                if trimmed and trimmed not in cleaned:
                    cleaned.append(trimmed)
                if len(cleaned) >= 12:
                    break
        self.custom_quotes = cleaned
        self.input_tracking = False
        return self


def user_data_dir() -> Path:
    if os.name == 'nt':
        base = Path(os.getenv('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
        return base / 'ProfMonkeyDesktop'
    return Path(os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config') / 'ProfMonkeyDesktop'


class ConfigStore:
    def __init__(self, folder: Path | None = None) -> None:
        self.folder = Path(folder) if folder else user_data_dir()
        self.path = self.folder / 'settings.json'

    def load(self) -> Settings:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict):
                return Settings()
            valid = {f.name for f in fields(Settings)}
            return Settings(**{k: v for k, v in raw.items() if k in valid}).validated()
        except (OSError, ValueError, TypeError, OverflowError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        settings.validated()
        fd, name = tempfile.mkstemp(dir=self.folder, prefix='.settings-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fp:
                json.dump(asdict(settings), fp, ensure_ascii=False, indent=2)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
