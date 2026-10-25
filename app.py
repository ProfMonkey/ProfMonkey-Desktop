"""ProfMonkey Desktop: offline desktop companion, v0.8 candidate."""
from pathlib import Path
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from core.config import ConfigStore
from core.history import History
from core.progress import ProgressStore
from ui.overlay import MonkeyOverlay
from ui.tray import MonkeyTray
from ui.colony import MonkeyColony


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    return root / relative


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('ProfMonkey Desktop')
    app.setOrganizationName('ProfMonkey')
    app.setQuitOnLastWindowClosed(False)
    icon = QIcon(str(resource_path('assets/icons/profmonkey.png')))
    app.setWindowIcon(icon)
    config = ConfigStore()
    settings = config.load()
    history = History(config.folder/'events.json', settings.history)
    progress = ProgressStore(config.folder/'progress.json', settings.progress_enabled)
    manifest = resource_path('assets/monkey/manifest.json')
    try:
        overlay = MonkeyOverlay(resource_path('assets/monkey/idle.png'),manifest,
                                settings=settings,history=history,progress=progress)
    except (OSError,ValueError,KeyError) as exc:
        QMessageBox.critical(None,'ProfMonkey 启动失败',f'角色素材加载失败：\n{exc}')
        return 2
    overlay.position_bottom_right()
    colony = MonkeyColony(overlay, resource_path('assets/monkey/idle.png'), manifest)
    tray = MonkeyTray(app, overlay, icon, config, manifest,
                     resource_path('site/index.html'), colony=colony)
    overlay.show()
    colony.set_count(settings.monkey_count)
    if not tray.has_tray:
        print('No system tray detected: right-click character to quit.',file=sys.stderr)
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
