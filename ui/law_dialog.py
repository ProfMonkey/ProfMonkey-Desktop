"""Read-only overview and explicit actions for fictional monkey legislation."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTextEdit, QVBoxLayout)
from core.governance import POLICIES, MonkeyLaws

RESULTS = {
    'adopted': '通过',
    'rejected': '否决',
    'stalemate': '僵持·原状不变',
}


class MonkeyLawDialog(QDialog):
    def __init__(self, colony, laws: MonkeyLaws, parent=None) -> None:
        super().__init__(parent)
        self.colony, self.laws = colony, laws
        self.setWindowTitle('📜 猴山自治 · 法令与试飞')
        self.resize(610, 565)
        self.setStyleSheet('''
          QDialog {background:#151d2c;color:#fce5c4}
          QLabel {color:#ffeacc}
          QTextEdit {background:#263248;color:#fce9cb;
            border:1px solid #5a6881;border-radius:12px;padding:12px}
          QPushButton {background:#384760;color:#f8ebce;
            border:1px solid #69758c;border-radius:10px;padding:11px}
          QPushButton#launch {background:#f6c778;color:#241c21;font-weight:850}
        ''')
        layout = QVBoxLayout(self)
        heading = QLabel('📜 猴山自治 · 今天有哪些规定？')
        heading.setStyleSheet('font-size:21px;font-weight:850')
        layout.addWidget(heading)
        info = QLabel('只有人工召开的猴山议会完整结束后才可能修改法令。'
                      '\n通过→生效；否决→废止；僵持→保持现状。'
                      '\n这些只影响猴子自己的虚构生活，不会改变真实电脑权限、'
                      '声音设置、文件或网络行为。')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary, 1)
        buttons = QHBoxLayout()
        launch = QPushButton('🚀 开始已批准的猴山试飞')
        launch.setObjectName('launch')
        launch.clicked.connect(self._launch)
        self.launch_button = launch
        reset = QPushButton('清空猴山法令')
        reset.clicked.connect(self._clear)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        buttons.addWidget(launch)
        buttons.addWidget(reset)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        rows = []
        for key, (title, effect) in POLICIES.items():
            status = '✅ 正在生效' if self.laws.active(key) else '⚪ 未生效'
            rows.append(f'{title} · {status}\n{effect}')
        if self.laws.history:
            history = ['\n—— 最近议会（最多24条）——']
            for row in reversed(self.laws.history[-10:]):
                history.append(f'{POLICIES[row["issue"]][0]}：{RESULTS[row["outcome"]]}')
            rows.extend(history)
        else:
            rows.append('\n还没有正式通过的议案。请先从「猴山议会」召开会议。')
        self.summary.setPlainText('\n\n'.join(rows))
        self.launch_button.setEnabled(self.laws.active('rocket_license'))

    def _launch(self) -> None:
        if self.colony.start_rocket_trial():
            self.accept()
            return
        QMessageBox.information(self, '试飞暂不可用',
                                '需先通过火箭许可证，且至少三只猴子在场（其中包含发明猴）。'
                                '\n暂停、专注、短剧、拖动或香蕉竞速期间不能试飞。')

    def _clear(self) -> None:
        if QMessageBox.question(self, '重置猴山法令',
                '确定重置全部三个虚构法令及表决历史吗？'
                '\n这不会清空猴际关系、猴山纪事或其他设置。'
                ) != QMessageBox.StandardButton.Yes:
            return
        self.colony.clear_monkey_laws()
        self.refresh()
