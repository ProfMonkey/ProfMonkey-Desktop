"""Small draggable, clickable desktop props; all interactions stay in this app."""
from __future__ import annotations
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QMenu, QWidget

PROPS = {
    'banana_tree': ('🍌', '香蕉树'),
    'blackboard': ('📋', '猴学黑板'),
    'trampoline': ('🛝', '蹦床'),
    'chair': ('🪑', '教授椅'),
    'mirror': ('🪞', '猴山镜子'),
}


class FurnitureWidget(QWidget):
    def __init__(self, kind: str, on_interact, on_remove, parent=None, *, always_on_top: bool = True):
        if kind not in PROPS:
            raise ValueError('unknown furniture prop')
        super().__init__(parent)
        self.kind = kind
        self.emoji, self.label = PROPS[kind]
        self.on_interact = on_interact
        self.on_remove = on_remove
        self._press: QPoint | None = None
        self._origin: QPoint | None = None
        self._dragged = False
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowDoesNotAcceptFocus)
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(124, 104)
        self.setToolTip(f'{self.label} · 左键互动，拖动摆放，右键收起')

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#c6a56e'), 1.5))
        painter.setBrush(QColor(29, 32, 47, 235))
        painter.drawRoundedRect(2, 2, self.width()-4, self.height()-4, 17, 17)
        painter.setPen(QColor('#fff0d2'))
        painter.setFont(QFont('Segoe UI Emoji', 34))
        painter.drawText(0, 4, self.width(), 58, Qt.AlignmentFlag.AlignCenter, self.emoji)
        painter.setFont(QFont('Microsoft YaHei UI', 10, QFont.Weight.DemiBold))
        painter.drawText(4, 65, self.width()-8, 27, Qt.AlignmentFlag.AlignCenter, self.label)
        painter.setPen(QColor('#c5b9a5'))
        painter.setFont(QFont('Microsoft YaHei UI', 7))
        painter.drawText(4, 86, self.width()-8, 13, Qt.AlignmentFlag.AlignCenter, '点击互动 · 拖动摆放')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragged = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is not None and self._origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            delta = current - self._press
            if abs(delta.x()) + abs(delta.y()) > 7:
                self._dragged = True
            if self._dragged:
                self.move(self._origin + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press is not None:
            if not self._dragged:
                self.on_interact(self)
            self._press = self._origin = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(f'收起{self.label}', lambda: self.on_remove(self))
        menu.exec(event.globalPos())
