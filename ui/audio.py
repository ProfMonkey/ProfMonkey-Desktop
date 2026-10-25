"""Low-volume opt-in event effects; software works if multimedia is unavailable."""
from pathlib import Path
from PySide6.QtCore import QUrl

try:
    from PySide6.QtMultimedia import QSoundEffect
except (ImportError, OSError):
    QSoundEffect = None


class SoundBank:
    def __init__(self, directory: Path, parent=None):
        self.effects = {}
        self.enabled = False
        if QSoundEffect is not None:
            for name in ('click','banana','slip','fall','win'):
                path = directory/f'{name}.wav'
                if path.is_file():
                    effect = QSoundEffect(parent)
                    effect.setSource(QUrl.fromLocalFile(str(path)))
                    effect.setVolume(.16)
                    self.effects[name]=effect

    def play(self,name):
        if self.enabled and name in self.effects:
            self.effects[name].play()
