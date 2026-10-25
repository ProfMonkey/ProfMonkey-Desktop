"""A very simple button-based, keyboard-accessible monkey count selector."""
from __future__ import annotations

from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QGridLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)


class MonkeyCountDialog(QDialog):
    def __init__(self, current: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🐒 猴山人口普查 · ProfMonkey')
        self.setMinimumWidth(380)
        self.setStyleSheet('''
        QDialog{background:#1D2031;color:#FFF5DD}
        QLabel{color:#FFF5DD}
        QPushButton[role="count"]{
            background:#2D324A;color:#FAE5C7;border:2px solid #404863;
            border-radius:13px;padding:15px 2px;font-size:19px;font-weight:700;
        }
        QPushButton[role="count"]:checked{background:#FFD17E;color:#22222C;border-color:#FFD17E}
        QPushButton[role="count"]:hover{border-color:#FFD17E}
        QPushButton{padding:8px}
        ''')
        root = QVBoxLayout(self)
        root.setSpacing(14)
        title = QLabel('想在桌面养几只猴子？')
        title.setStyleSheet('font-size:19px;font-weight:800;')
        root.addWidget(title)
        subtitle = QLabel('1～6 只 · 每只都独立走路、睡觉、被戳和拖拽')
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet('color:#B6BED2')
        root.addWidget(subtitle)
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        gridbox = QWidget(self)
        grid = QGridLayout(gridbox)
        grid.setSpacing(10)
        for count in range(1, 7):
            b = QPushButton(f'🐒 × {count}')
            b.setProperty('role', 'count')
            b.setCheckable(True)
            b.setChecked(count == current)
            self.buttons.addButton(b, count)
            grid.addWidget(b, (count-1)//3, (count-1)%3)
        root.addWidget(gridbox)
        hint = QLabel('⚡ 数量立即生效；4～6 只会占用更多内存和 CPU。\n'
                      '多只猴子不监听键盘，也不会改动真实窗口。')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#D9C3A0;font-size:12px')
        root.addWidget(hint)
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        actions.button(QDialogButtonBox.StandardButton.Ok).setText('确认，放猴子出来 🍌')
        actions.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        root.addWidget(actions)

    def selected(self) -> int:
        return self.buttons.checkedId()
