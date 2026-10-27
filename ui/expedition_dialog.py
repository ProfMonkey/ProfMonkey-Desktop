"""User-driven expedition board and offline monkey newspaper."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout,
                               QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QVBoxLayout)
from core.expeditions import (MISSIONS, RESULTS, Explorer, plan_expedition,
                              newspaper)


class ExpeditionDialog(QDialog):
    def __init__(self, colony, parent=None) -> None:
        super().__init__(parent)
        self.colony = colony
        self.setWindowTitle('🧭 猴山探险局 · 小队和日报')
        self.resize(690, 710)
        self.setStyleSheet('''
          QDialog {background:#151d2e;color:#ffedcf}
          QLabel {color:#ffedcf}
          QComboBox,QPlainTextEdit {background:#25334a;color:#fff0d6;
             padding:10px;border:1px solid #5d6c87;border-radius:11px}
          QPushButton {background:#3b4d67;color:#ffeac5;padding:11px;
             border:1px solid #60718a;border-radius:11px}
          QPushButton#start {background:#f6ca7d;color:#242022;font-weight:850}
        ''')
        layout = QVBoxLayout(self)
        heading = QLabel('🧭 猴山探险局 · 派两只以上的猴子出去看看')
        heading.setStyleSheet('font-size:20px;font-weight:850')
        layout.addWidget(heading)
        intro = QLabel('小队有三幕剧情，性格、关系和已通过的猴山法令影响结果。'
                       '\n只有最后一幕正常结束，才会真正获得香蕉、科研点或声望。'
                       '\n这是虚构世界里的资源，没有真钱、GPS、后台下载或现实任务。')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(QLabel('🎯 选择一条探险路线'))
        self.mission = QComboBox()
        for kind, (title, _desc) in MISSIONS.items():
            self.mission.addItem(title, kind)
        self.mission.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.mission)
        layout.addWidget(QLabel('🐒 选择参与小队的角色（2–6位）'))
        self.checks = []
        for idx, pet in enumerate(colony.monkeys):
            checkbox = QCheckBox(f'#{idx+1} {pet.display_name} · {pet.personality}')
            checkbox.setEnabled(pet.isVisible())
            checkbox.setChecked(idx < 2)
            checkbox.toggled.connect(self.refresh)
            self.checks.append(checkbox)
            layout.addWidget(checkbox)
        layout.addWidget(QLabel('🧮 任务推演：预估奖励，只取决于游戏内猴子数据'))
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(63)
        layout.addWidget(self.preview)
        row = QHBoxLayout()
        self.launch = QPushButton('🚀 开始三幕探险')
        self.launch.setObjectName('start')
        self.launch.clicked.connect(self._launch)
        row.addWidget(self.launch)
        cancel = QPushButton('⛔ 取消当前探险')
        cancel.clicked.connect(self._cancel)
        row.addWidget(cancel)
        layout.addLayout(row)
        layout.addWidget(QLabel('🗞️ 猴山日报 · 离线内政与实验成果'))
        self.bulletin = QPlainTextEdit()
        self.bulletin.setReadOnly(True)
        self.bulletin.setMinimumHeight(190)
        layout.addWidget(self.bulletin, 1)
        bottom = QHBoxLayout()
        refresh = QPushButton('🔄 刷新日报')
        refresh.clicked.connect(self.refresh)
        clear = QPushButton('🗑 清空探险档案')
        clear.clicked.connect(self._clear)
        exit_button = QPushButton('关闭')
        exit_button.clicked.connect(self.accept)
        bottom.addWidget(refresh)
        bottom.addWidget(clear)
        bottom.addWidget(exit_button)
        layout.addLayout(bottom)
        self.refresh()

    def selected(self) -> tuple[int, ...]:
        return tuple(i for i, cb in enumerate(self.checks)
                     if cb.isChecked() and cb.isEnabled())

    def refresh(self, *_args) -> None:
        journal = self.colony.expeditions
        if journal is None:
            self.preview.setText('探险档案尚未初始化。')
            self.launch.setEnabled(False)
            return
        names = tuple(p.display_name for p in self.colony.monkeys)
        self.bulletin.setPlainText(newspaper(journal, self.colony.laws, names))
        indices = self.selected()
        if len(indices) < 2:
            self.preview.setText('至少需要两只可见的猴子才能组成小队。')
            self.launch.setEnabled(False)
            return
        crew = tuple(Explorer(i, self.colony.monkeys[i].personality) for i in indices)
        laws = frozenset(key for key in ('banana_rules', 'quiet_hours', 'rocket_license')
                          if self.colony.laws is not None and self.colony.laws.active(key))
        try:
            plan = plan_expedition(self.mission.currentData(),
                                   crew, self.colony.relationships, laws)
        except ValueError:
            self.preview.setText('队员或路线无效。')
            self.launch.setEnabled(False)
            return
        self.preview.setText(
            f'预估结果：{RESULTS[plan.outcome]}（协作分 {plan.score}）\n'
            f'预计获得：🍌{plan.rewards[0]} | 🔬{plan.rewards[1]} | ⭐{plan.rewards[2]}'
            + (' · 猴山法令加成已生效' if plan.law_boost else ''))
        self.launch.setEnabled(True)

    def _launch(self) -> None:
        if self.colony.start_expedition(self.mission.currentData(), self.selected()):
            self.accept()
        else:
            QMessageBox.information(
                self, '探险暂不可用',
                '请至少选择两只可见、空闲猴子；暂停、专注、其他短剧或'
                '香蕉竞速正在进行时不能出发。')

    def _cancel(self) -> None:
        self.colony.cancel_expedition()
        self.refresh()

    def _clear(self) -> None:
        if QMessageBox.question(
            self, '清空猴山探险档案',
            '是否永久删除本机全部探险资源、出勤记录及日报历史？'
            '\n猴际关系、猴山法令和连续剧情不会被删除。'
        ) != QMessageBox.StandardButton.Yes:
            return
        self.colony.clear_expeditions()
        self.refresh()
