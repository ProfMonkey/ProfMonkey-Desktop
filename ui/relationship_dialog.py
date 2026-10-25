"""Local relationship dashboard and user-controlled reconciliation actions."""
from __future__ import annotations
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout)
from core.profiles import clean_profiles
from core.relationships import RelationshipStore


class RelationshipDialog(QDialog):
    def __init__(self, store: RelationshipStore, profiles: list[dict], count: int, parent=None):
        super().__init__(parent)
        self.store = store
        self.profiles = clean_profiles(profiles)
        self.count = max(1, min(6, count))
        self.setWindowTitle('🤝 猴山关系档案')
        self.resize(520, 480)
        self.setStyleSheet('''QDialog{background:#151923;color:#ffedcf} QLabel{color:#ffedcf}
            QComboBox{background:#282b3a;color:#fff0d7;padding:7px;border:1px solid #595465;border-radius:7px}
            QPushButton{background:#373849;color:#fff0d7;border:1px solid #595465;border-radius:9px;padding:9px}
            QPushButton#primary{background:#e9b85e;color:#211b1f;font-weight:700}''')
        root = QVBoxLayout(self)
        title = QLabel('🤝 猴山关系档案')
        title.setStyleSheet('font-size:23px;font-weight:850')
        root.addWidget(title)
        root.addWidget(QLabel('猴子会记住一起开会、抢香蕉和碰撞的经历。数据只保存在本机。'))
        self.list_label = QLabel()
        self.list_label.setWordWrap(True)
        self.list_label.setStyleSheet('background:#222638;border-radius:10px;padding:12px;line-height:1.5')
        root.addWidget(self.list_label, 1)
        row = QHBoxLayout()
        self.first = QComboBox(); self.second = QComboBox()
        for i in range(self.count):
            name = self.profiles[i]['name']
            self.first.addItem(f'{i+1}. {name}', i)
            self.second.addItem(f'{i+1}. {name}', i)
        if self.count > 1:
            self.second.setCurrentIndex(1)
        row.addWidget(self.first); row.addWidget(self.second)
        root.addLayout(row)
        actions = QHBoxLayout()
        reconcile = QPushButton('🕊 安排和解'); reconcile.clicked.connect(self.reconcile)
        mentor = QPushButton('🎓 设为师徒'); mentor.clicked.connect(self.set_mentor)
        actions.addWidget(reconcile); actions.addWidget(mentor)
        root.addLayout(actions)
        close = QPushButton('关闭'); close.clicked.connect(self.accept); close.setObjectName('primary')
        root.addWidget(close)
        self.refresh()

    def refresh(self) -> None:
        lines = []
        for i in range(self.count):
            mentor = self.store.mentor_of(i)
            if mentor is not None and mentor < self.count:
                lines.append(f'🎓 {self.profiles[mentor]["name"]} → {self.profiles[i]["name"]}：师徒关系')
            for j in range(i+1, self.count):
                rel = self.store.get(i, j)
                lines.append(f'{self.profiles[i]["name"]} ↔ {self.profiles[j]["name"]}：{rel["label"]}  '
                             f'好感 {rel["bond"]:+d} · 竞争 {rel["rivalry"]} · 信任 {rel["trust"]}')
        self.list_label.setText('\n'.join(lines) if lines else '目前只有一只猴子。再召唤一只，才能产生复杂的人际关系。')

    def _pair(self):
        a, b = self.first.currentData(), self.second.currentData()
        if a == b:
            QMessageBox.information(self, '选择两只猴子', '师徒或和解需要选择两只不同的猴子。')
            return None
        return a, b

    def reconcile(self) -> None:
        pair = self._pair()
        if pair is not None:
            self.store.reconcile(*pair)
            self.refresh()

    def set_mentor(self) -> None:
        pair = self._pair()
        if pair is not None:
            mentor, student = pair
            self.store.set_mentor(mentor, student)
            self.refresh()
