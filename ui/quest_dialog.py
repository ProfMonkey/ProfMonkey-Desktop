"""Display today's local missions and completion points."""
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout
from core.quests import QuestBoard


class QuestDialog(QDialog):
    def __init__(self, board: QuestBoard, monkey_count: int, parent=None):
        super().__init__(parent)
        self.board = board
        self.monkey_count = monkey_count
        self.setWindowTitle('📜 今日猴山任务')
        self.resize(490, 400)
        self.setStyleSheet('''QDialog{background:#151923;color:#ffedcf} QLabel{color:#ffedcf}
            QPushButton{background:#e9b85e;color:#211b1f;border:0;border-radius:9px;padding:10px;font-weight:700}''')
        root = QVBoxLayout(self)
        title = QLabel('📜 今日猴山任务')
        title.setStyleSheet('font-size:24px;font-weight:850')
        root.addWidget(title)
        self.summary = QLabel()
        root.addWidget(self.summary)
        self.tasks = QLabel()
        self.tasks.setWordWrap(True)
        self.tasks.setStyleSheet('background:#222638;border-radius:10px;padding:14px;font-size:14px')
        root.addWidget(self.tasks, 1)
        note = QLabel('任务只统计你主动触发的猴山动作；不监控键盘、应用或学习内容。完成当天全部任务可获得 3 点猴学积分。')
        note.setWordWrap(True); note.setStyleSheet('color:#b9b4c3;font-size:12px')
        root.addWidget(note)
        close = QPushButton('知道了'); close.clicked.connect(self.accept); root.addWidget(close)
        self.refresh()

    def refresh(self) -> None:
        data = self.board.snapshot(self.monkey_count)
        self.summary.setText(f'{data["date"]}   ·   猴学积分 {data["points"]}   ·   完成天数 {data["completed_days"]}')
        lines = []
        for task in data['tasks']:
            if task['locked']:
                status = '🔒 需要至少两只猴子'
            elif task['done']:
                status = '✅ 已完成'
            else:
                status = f'⏳ 进度 {task["display"]}'
            lines.append(f'{task["title"]}\n{task["description"]}\n{status}')
        if data['all_complete']:
            lines.append('\n🏆 今日任务全部完成！奖励已发放。')
        self.tasks.setText('\n\n'.join(lines))
