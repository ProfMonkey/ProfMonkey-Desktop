"""v0.19 native observer: an opt-in window onto the fictional monkey society.

This only reads journal/relationship snapshots. Ambient encounters use the
existing low-frequency director. The user explicitly enables them separately.
"""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout,
                               QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QVBoxLayout)
from core.civic_society import society_report


class SocietyDialog(QDialog):
    def __init__(self, colony, save_settings=None, parent=None):
        super().__init__(parent)
        self.colony = colony
        self.save_settings = save_settings
        self.setWindowTitle('🐒🏛️ 猴山自主社会 · v0.19')
        self.resize(780, 710)
        self.setStyleSheet("""
            QDialog {background:#101c2e;color:#fbeaca}
            QLabel,QCheckBox {color:#fbeaca}
            QComboBox,QPlainTextEdit {background:#1c3048;color:#fcead2;
                border:1px solid #8190a3;border-radius:10px;padding:9px}
            QPushButton {background:#354c67;color:#fff0d4;
                border:1px solid #7e94a9;border-radius:9px;padding:10px}
            QPushButton#observe {background:#eed18d;color:#231e1f;font-weight:900}
        """)
        layout = QVBoxLayout(self)
        heading = QLabel('🌆 这一次，猴子真的开始有自己的社会')
        heading.setStyleSheet('font-size:22px;font-weight:900')
        layout.addWidget(heading)
        detail = QLabel('角色岗位由已经建好的建筑决定；历史结局、'
                        '法令和猴际关系影响合作、创新、分歧和虚构阵营。'
                        '\n这里所有结果都来自本地游戏资料，不收集任何桌面行为。')
        detail.setWordWrap(True)
        layout.addWidget(detail)
        self.enabled = QCheckBox('🐒 开启自治行为（仅猴山模式；默认关闭）')
        self.enabled.setChecked(bool(colony.primary.settings.civic_autonomy))
        layout.addWidget(self.enabled)
        self.ambient = QCheckBox('💬 允许低频自动偶遇（独立开关；默认关闭）')
        self.ambient.setChecked(bool(colony.primary.settings.ambient_encounters))
        layout.addWidget(self.ambient)
        note = QLabel('🔕 安静模式、专注、暂停、隐藏时不主动进行自治表演；'
                      '现有「猴山安静公约」同样会禁止自动偶遇。'
                      '\n不会自动制造剧情弹窗，也不会自动领取资源。')
        note.setWordWrap(True)
        note.setStyleSheet('color:#b9d2dc')
        layout.addWidget(note)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel('🏛️ 文明快照 · 六猴岗位与观点'))
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report, 1)
        layout.addWidget(QLabel('🎭 手动安排一次真正的角色碰面（不会扣除资源）'))
        pair = QHBoxLayout()
        self.first = QComboBox()
        self.second = QComboBox()
        for idx, pet in enumerate(colony.monkeys):
            label = f'#{idx+1} {pet.display_name} · {pet.personality}'
            self.first.addItem(label, idx)
            self.second.addItem(label, idx)
        if colony.count >= 2:
            self.second.setCurrentIndex(1)
        pair.addWidget(self.first)
        pair.addWidget(self.second)
        layout.addLayout(pair)
        self.observe = QPushButton('▶️ 安排一次历史主题偶遇')
        self.observe.setObjectName('observe')
        self.observe.clicked.connect(self._observe)
        layout.addWidget(self.observe)
        actions = QHBoxLayout()
        update = QPushButton('↻ 重新观察猴山')
        update.clicked.connect(self.refresh)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        actions.addWidget(update)
        actions.addWidget(close)
        layout.addLayout(actions)
        self.enabled.toggled.connect(self._toggle_autonomy)
        self.ambient.toggled.connect(self._toggle_ambient)
        self.first.currentIndexChanged.connect(self.refresh)
        self.second.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def _persist(self):
        if self.save_settings is not None:
            self.save_settings()

    def _toggle_autonomy(self, value):
        self.colony.set_civic_autonomy(value)
        self._persist()
        self.refresh()

    def _toggle_ambient(self, value):
        self.colony.set_ambient_encounters(value)
        self._persist()
        self.refresh()

    def refresh(self, *_unused):
        snapshot = self.colony.society_snapshot()
        if snapshot is None:
            self.report.setPlainText('需要加载本地猴山档案。')
            self.observe.setEnabled(False)
            return
        self.report.setPlainText(society_report(snapshot))
        active = bool(self.colony.primary.settings.civic_autonomy)
        monkey_mode = self.colony.primary.settings.mode == 'MONKEY'
        self.status.setText('✅ 正在影响猴山自主行为' if active and monkey_mode else
                            '🌙 自治行为已开启，但当前是安静模式' if active else
                            '🔒 仅供查看：自主行为关闭，不改变原来的猴子行动')
        self.observe.setEnabled(active and monkey_mode and
                                self.colony.count >= 2 and
                                self.first.currentData() != self.second.currentData())

    def _observe(self):
        # Reject direct calls too; a disabled visual button alone is not a
        # sufficient consent gate for explicitly opted-in background features.
        a, b = self.first.currentData(), self.second.currentData()
        if (not self.colony.primary.settings.civic_autonomy or
                self.colony.primary.settings.mode != 'MONKEY' or
                type(a) is not int or type(b) is not int or a == b):
            return
        if not self.colony.demo_pair(a, b):
            QMessageBox.information(
                self, '🐒 猴山社会 · 暂时无法互动',
                '需要开启自治行为和猴山模式，以及两只不同、可见、空闲的猴子。'
                '\n暂停、专注、拖拽、其他短剧或香蕉竞速期间不能抢占角色。')
        self.refresh()
