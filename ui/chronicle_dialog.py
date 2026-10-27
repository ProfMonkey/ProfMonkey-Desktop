"""User-controlled fictional colony casebook; nothing scans the real desktop."""
from __future__ import annotations
from typing import Callable
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout,
                               QLabel, QMessageBox, QPlainTextEdit, QPushButton,
                               QVBoxLayout)
from core.chronicle import ChronicleStore, TITLES


class ChronicleDialog(QDialog):
    def __init__(self, colony, store: ChronicleStore,
                 on_enabled_changed: Callable[[bool], None], parent=None) -> None:
        super().__init__(parent)
        self.colony = colony
        self.store = store
        self._on_enabled_changed = on_enabled_changed
        self.setWindowTitle('📖 猴山纪事 · 三章连续剧情')
        self.resize(620, 580)
        self.setStyleSheet('''
          QDialog {background:#151a29;color:#ffeccd}
          QLabel {color:#f9e7c8}
          QComboBox,QPlainTextEdit {background:#222b3e;color:#fff2d5;
               padding:8px;border:1px solid #59647a;border-radius:9px}
          QPushButton {background:#343f58;color:#ffeccd;border:1px solid #67748a;
               padding:10px;border-radius:10px}
          QPushButton#primary {background:#e9b85e;color:#211b1f;font-weight:800}
        ''')
        layout = QVBoxLayout(self)
        heading = QLabel('📖 猴山纪事 · 真实发生在虚构猴山里的事故')
        heading.setStyleSheet('font-size:19px;font-weight:850')
        layout.addWidget(heading)
        note = QLabel('猴山会议、香蕉争夺或专属相遇结束后，会留下可续写的线索。\n'
                      '每个案件有三章与两种关系结局。只记录猴子编号、虚构事件与成长值。')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.enabled = QCheckBox('启用本地猴山纪事（默认关闭，不自动播放后续章节）')
        self.enabled.setChecked(store.enabled)
        self.enabled.toggled.connect(self._toggle)
        layout.addWidget(self.enabled)
        layout.addWidget(QLabel('待续案件 · 选择一章手动播放'))
        self.cases = QComboBox()
        layout.addWidget(self.cases)
        self.progress = QLabel()
        self.progress.setWordWrap(True)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel('🎖 猴山成长 · 仅完整章节结算'))
        self.growth = QLabel()
        self.growth.setWordWrap(True)
        layout.addWidget(self.growth)
        layout.addWidget(QLabel('最近的故事记录（最多保存 100 条）'))
        self.events = QPlainTextEdit()
        self.events.setReadOnly(True)
        self.events.setMinimumHeight(130)
        layout.addWidget(self.events)
        buttons = QHBoxLayout()
        self.play = QPushButton('▶ 上演下一章')
        self.play.setObjectName('primary')
        self.play.clicked.connect(self._play)
        reset = QPushButton('清空所有纪事')
        reset.clicked.connect(self._clear)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        buttons.addWidget(self.play)
        buttons.addWidget(reset)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.cases.currentIndexChanged.connect(self._update_progress)
        self.refresh()

    def _toggle(self, checked: bool) -> None:
        self._on_enabled_changed(checked)
        self.refresh()

    def refresh(self) -> None:
        self.cases.blockSignals(True)
        self.cases.clear()
        self.cases.blockSignals(False)
        for case in self.store.pending(member_count=self.colony.count):
            a = self.colony.monkeys[case['first']].display_name
            b = self.colony.monkeys[case['second']].display_name
            label = f'{case["title"]} · 第 {case["stage"]+1}/3 章 · {a} 与 {b}'
            self.cases.addItem(label, case['id'])
        self.cases.setEnabled(self.store.enabled and self.cases.count() > 0)
        self.play.setEnabled(self.store.enabled and self.cases.count() > 0)
        self._update_progress()
        if self.store.enabled:
            lines = []
            for monkey in self.colony.monkeys:
                stats = self.store.growth_for(monkey.monkey_index)
                lines.append(f'{monkey.display_name}：Lv.{stats["level"]} {stats["title"]}'
                             f' · 研究{stats["research"]} / 调皮{stats["mischief"]}'
                             f' / 友善{stats["empathy"]}')
            self.growth.setText('\n'.join(lines))
            self.events.setPlainText('\n'.join(
                f'{TITLES[e["kind"]]} · {e["event"]} · 第{e["chapter"]}章'
                for e in self.store.events[-25:][::-1]) or '暂无记录。完成一场猴际互动后会产生案件。')
        else:
            self.growth.setText('纪事尚未开启，成长值不会自动记录。')
            self.events.setPlainText('默认不保存任何猴山纪事。')

    def _update_progress(self, _index: int = 0) -> None:
        cid = self.cases.currentData()
        if cid is None:
            self.progress.setText('暂无可续写案件。先在菜单里让猴子们开会、抢香蕉或互动。')
            return
        case = next((c for c in self.store.pending(member_count=self.colony.count)
                     if c['id'] == cid), None)
        if case is not None:
            self.progress.setText(f'下一幕：{case["title"]} · 第 {case["stage"]+1} 章。'
                                  '只有完整播完两幕后才能推进；拖动或暂停会取消。')

    def _play(self) -> None:
        cid = self.cases.currentData()
        if cid is not None and self.colony.play_chronicle_chapter(cid):
            self.accept()
        else:
            QMessageBox.information(self, '猴山纪事', '两只猴子必须可见、空闲，且目前不能正在专注或表演其他短剧。')

    def _clear(self) -> None:
        if QMessageBox.question(self, '清空猴山纪事',
                '确认永久清除本机的连续剧情、猴子成长值与纪事记录吗？'
                ' 猴山关系档案和其他设置不会被清除。') != QMessageBox.StandardButton.Yes:
            return
        if self.colony._active_chapter is not None:
            self.colony.cancel_duo()
        self.store.clear()
        self.refresh()
