"""Keep one Qt QApplication alive for the entire offscreen test session.

Some Windows PySide6 versions crash *after* pytest prints "all passed" when
many short-lived QApplication objects and native audio/window handles unwind
during Python interpreter shutdown. Release Qt objects explicitly while
Python/Qt modules are still alive. Real GUI applications are unaffected.
"""
from __future__ import annotations
import os
import pytest


@pytest.fixture(scope='session', autouse=True)
def session_qt_lifecycle():
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        yield
        return
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication, QEvent
    except (ImportError, OSError):
        yield
        return
    app = QApplication.instance() or QApplication([])
    yield
    for widget in list(QApplication.topLevelWidgets()):
        try:
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass
    try:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        # Explicit QObject disposal avoids fragile C++ Qt shutdown ordering
        # while Python tears down globals and test module references.
        import shiboken6
        shiboken6.delete(app)
    except RuntimeError:
        pass
