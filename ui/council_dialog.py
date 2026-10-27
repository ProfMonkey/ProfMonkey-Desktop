"""Manual multi-monkey council control surface; preview never mutates relationships."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout,
)
from core.council import ISSUES, RESULT_NAMES, Seat, VOTE_NAMES, derive_factions, prepare_council
from core.governance import POLICIES


class CouncilDialog(QDialog):
    def __init__(self, colony, parent=None) -> None:
        super().__init__(parent)
        self.colony = colony
        self.setWindowTitle('🗳 猴山议会 · 自选参会成员')
        self.resize(610, 650)
        self.setStyleSheet('''
            QDialog{background:#151b2b;color:#ffe9c7}
            QLabel{color:#ffe9c7}
            QComboBox,QTextEdit{background:#252e43;color:#fbe9d0;
              border:1px solid #505f78;border-radius:10px;padding:8px}
            QPushButton{background:#3b455e;color:#ffe9c7;
              border:1px solid #66718a;border-radius:10px;padding:11px}
            QPushButton#primary{background:#f0c679;color:#231b20;font-weight:800}
        ''')
        layout = QVBoxLayout(self)
        title = QLabel('🗳 猴山议会 · 三猴以上才开会')
        title.setStyleSheet('font-size:21px;font-weight:850')
        layout.addWidget(title)
        help_text = QLabel('每只猴子的性格与真实猴际关系都会改变它的虚构投票。'
                           '\n开会要经过三幕，全部播完才改变猴际关系。'
                           '\n预览不会修改存档，且议会不会自动弹出。')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        layout.addWidget(QLabel('今天讨论什么？'))
        self.issue = QComboBox()
        for key, (title, _question) in ISSUES.items():
            self.issue.addItem(title, key)
        layout.addWidget(self.issue)
        layout.addWidget(QLabel('参加投票的猴子（3～6只）'))
        self.checks: list[QCheckBox] = []
        for index, pet in enumerate(colony.monkeys):
            check = QCheckBox(f'#{index+1}  {pet.display_name}')
            check.setChecked(index < 3)
            check.setEnabled(pet.isVisible())
            layout.addWidget(check)
            self.checks.append(check)
            check.toggled.connect(self.refresh)
        self.issue.currentIndexChanged.connect(self.refresh)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        buttons = QHBoxLayout()
        self.start_button = QPushButton('🎭 召开三幕议会')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.launch)
        close_button = QPushButton('关闭')
        close_button.clicked.connect(self.reject)
        buttons.addWidget(self.start_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self.refresh()

    def selected(self) -> tuple[int, ...]:
        return tuple(i for i, cb in enumerate(self.checks)
                     if cb.isChecked() and cb.isEnabled())

    def refresh(self, *_args) -> None:
        members = self.selected()
        if len(members) < 3:
            self.preview.setPlainText('至少选择三只可见猴子。')
            self.start_button.setEnabled(False)
            return
        seats = tuple(Seat(i, self.colony.monkeys[i].personality) for i in members)
        try:
            result = prepare_council(self.issue.currentData(), seats, self.colony.relationships)
            factions = derive_factions(
                tuple(Seat(i, pet.personality) for i, pet in enumerate(self.colony.monkeys)),
                self.colony.relationships)
        except ValueError:
            self.start_button.setEnabled(False)
            self.preview.setPlainText('成员或议题无效，请重新选择。')
            return
        vote_rows = [
            f'{self.colony.monkeys[index].display_name}：{VOTE_NAMES[vote]}'
            for index, vote in result.votes
        ]
        if factions:
            faction_rows = ['、'.join(self.colony.monkeys[i].display_name for i in group)
                            for group in factions]
            faction_label = '\n'.join(f'合作小组 {j+1}：{text}'
                                      for j, text in enumerate(faction_rows))
        else:
            faction_label = '目前没有关系足够紧密的合作小组。'
        self.preview.setPlainText(
            '虚构议案（仅预览）：' + ISSUES[result.issue][1] +
            '\n\n预测选票：\n' + '\n'.join(vote_rows) +
            '\n\n预测结果：' + RESULT_NAMES[result.result] +
            '\n\n📜 已投票通过后会影响猴山生活：\n' + POLICIES[result.issue][1] +
            '\n当前法令：' + ('已生效' if self.colony.laws is not None and self.colony.laws.active(result.issue) else '未生效') +
            '\n\n🤝 当前猴际合作网络：\n' + faction_label +
            '\n\n合作小组是根据关系档案动态计算的，并非永久阵营。')
        self.start_button.setEnabled(True)

    def launch(self) -> None:
        if self.colony.start_council(self.issue.currentData(), self.selected()):
            self.accept()
            return
        QMessageBox.information(self, '猴山议会暂不可用',
            '至少三只猴子必须处于可见、空闲状态；其他短剧、投喂竞速、'
            '暂停、专注或拖动中不能召开新议会。')
