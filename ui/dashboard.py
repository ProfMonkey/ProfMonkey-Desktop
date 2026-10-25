"""Optional local achievements + in-memory pet stats, never OS activity data."""
from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar,
                               QScrollArea, QWidget, QPushButton, QMessageBox)
from core.progress import BADGES, ProgressStore
from core.state import PetState

_STYLE = """
QDialog { background:#12182A; color:#F3EBDD; font-family:'Microsoft YaHei'; }
QLabel { color:#F3EBDD; }
QLabel#h1 { font-size:22px; font-weight:800; color:#F9D77A; }
QLabel#note { color:#B8B5C5; }
QProgressBar { background:#29344B; border:0; border-radius:6px; height:10px; }
QProgressBar::chunk { background:#E9AF50; border-radius:6px; }
QPushButton { background:#F2BF63; color:#1B2036; padding:9px 12px; font-weight:bold; border-radius:8px; }
"""


class Dashboard(QDialog):
    def __init__(self, state: PetState, progress: ProgressStore | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('ProfMonkey · 猴学档案')
        self.resize(460, 560)
        self.setStyleSheet(_STYLE)
        layout = QVBoxLayout(self)
        header = QLabel('🐒 猴学研究院 · 档案室')
        header.setObjectName('h1')
        layout.addWidget(header)
        for name, value, maximum in [('精力', state.energy, 100), ('心情', state.mood+100, 200),
                                     ('好奇心', state.curiosity, 100), ('调皮程度', state.mischief, 100)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            bar = QProgressBar(); bar.setRange(0, maximum); bar.setValue(round(value)); bar.setTextVisible(False)
            row.addWidget(bar, 1)
            layout.addLayout(row)
        layout.addWidget(QLabel('🏅 猴学勋章'))
        if progress is None or not progress.enabled:
            message = QLabel('当前未启用档案记录。可在「设置」里自愿开启。\n无需监听键盘、截图或联网。')
            message.setWordWrap(True)
            layout.addWidget(message)
        else:
            unlocked = progress.unlocked()
            box = QWidget(); inner = QVBoxLayout(box)
            for key, name, counter, target in BADGES:
                current = progress.counts[counter]
                text = ('✅' if key in unlocked else '🔒') + f'  {name}    {min(target,current)}/{target}'
                label = QLabel(text); label.setMinimumHeight(32)
                inner.addWidget(label)
            inner.addStretch()
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(box)
            scroll.setStyleSheet('QScrollArea { background: transparent; border:0; }')
            layout.addWidget(scroll, 1)
            summary = progress.counts
            layout.addWidget(QLabel(f"互动 {summary['taps']} 次 · 投喂 {summary['feeds']} 次 · "
                                    f"短剧 {summary['stories']} 次 · 专注 {summary['focus_minutes']} 分钟"))
            clear = QPushButton('清除本地勋章数据')
            clear.clicked.connect(self._clear)
            layout.addWidget(clear)
        foot = QLabel('档案只存储你主动开启后与猴子的互动次数，不记录系统活动。')
        foot.setObjectName('note'); foot.setWordWrap(True)
        layout.addWidget(foot)
        close = QPushButton('关闭档案')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.progress = progress

    def _clear(self) -> None:
        if self.progress is None:
            return
        if QMessageBox.question(self, '清除本地档案', '确定删除已保存的猴学勋章进度吗？') == QMessageBox.StandardButton.Yes:
            self.progress.clear()
            self.accept()
