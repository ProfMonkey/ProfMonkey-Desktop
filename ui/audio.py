"""Optional desktop pet sound effects; do not initialize multimedia if muted.

Default-muted pets create zero QSoundEffect/native audio objects. Effects are
created only after the user explicitly enables sound, released on mute/quit.
This is important for multiple pets and headless Windows regression tests.
"""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QUrl


class SoundBank:
    def __init__(self, directory: Path, parent=None):
        self.directory = Path(directory)
        self.parent = parent
        self.effects = {}
        self.enabled = False

    def set_enabled(self, enabled: bool) -> None:
        value = bool(enabled)
        if not value:
            self.enabled = False
            for effect in self.effects.values():
                effect.stop()
                effect.deleteLater()
            self.effects.clear()
            return
        if self.enabled:
            return
        self.enabled = True
        try:
            # Late import avoids loading an audio backend for default-muted pets.
            from PySide6.QtMultimedia import QSoundEffect
        except (ImportError, OSError):
            return
        for name in ('click', 'banana', 'slip', 'fall', 'win'):
            path = self.directory / f'{name}.wav'
            if path.is_file():
                effect = QSoundEffect(self.parent)
                effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
                effect.setVolume(.16)
                self.effects[name] = effect

    def play(self, name: str) -> None:
        if self.enabled and name in self.effects:
            self.effects[name].play()
