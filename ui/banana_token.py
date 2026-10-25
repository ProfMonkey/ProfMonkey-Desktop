"""Small, clickable transparent overlay for the shared banana-race feature."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import QWidget


class BananaTokenOverlay(QWidget):
    WIDTH = 88
    HEIGHT = 76

    def __init__(self, on_cancel, parent=None):
        super().__init__(parent)
        self._on_cancel = on_cancel
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowTitle('ProfMonkey · 公共香蕉')
        self.setToolTip('🍌 猴子们正在抢香蕉；点击取消这次争夺')
        # Only the badge itself receives input; all other pixels stay transparent.
        self.setMask(QRegion(QRect(10, 4, 68, 66)))

    @property
    def center_x(self) -> float:
        return float(self.x() + self.width() / 2)

    def paintEvent(self, event):  # noqa: N802 - Qt callback name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor('#6C4B20'), 2.0))
        painter.setBrush(QColor('#FFF0C8'))
        painter.drawRoundedRect(10, 7, 68, 60, 18, 18)

        # Banana silhouette: a warm curved crescent with a small brown stem.
        banana = QPainterPath()
        banana.moveTo(25, 20)
        banana.cubicTo(35, 38, 49, 45, 64, 31)
        banana.cubicTo(61, 48, 43, 56, 29, 43)
        banana.cubicTo(21, 36, 20, 27, 25, 20)
        banana.closeSubpath()
        painter.setBrush(QColor('#FFD84F'))
        painter.drawPath(banana)
        painter.setPen(QPen(QColor('#8A5A28'), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(25, 20, 22, 16)
        painter.setPen(QPen(QColor('#B77A2B'), 1.5))
        painter.drawLine(29, 25, 34, 30)
        painter.end()

    def mousePressEvent(self, event):  # noqa: N802 - Qt callback name
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_cancel()
            event.accept()
            return
        super().mousePressEvent(event)
