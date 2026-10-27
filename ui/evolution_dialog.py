"""An opt-in, three-scene native history book. No scene commits on cancel."""
from __future__ import annotations
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)
from core.city_evolution import (LEGACY_EVENTS, ROUTES, evolution_report,
                                 legacy_status, prepare_evolution)


class EvolutionDialog(QDialog):
    def __init__(self, colony, parent=None):
        super().__init__(parent)
        self.colony = colony
        self.plan = None
        self.scene_index = -1
        self.setWindowTitle('📜 猴山历史与文明演化 · v0.18')
        self.resize(760, 690)
        self.setStyleSheet("""
            QDialog {background:#111d2e;color:#ffefd1}
            QLabel {color:#ffefd1}
            QComboBox,QPlainTextEdit {background:#1b2c44;color:#ffefd1;
                border:1px solid #7186a1;border-radius:8px;padding:8px}
            QPushButton {background:#334c67;color:#fff1d6;
                border:1px solid #6f8ea6;border-radius:8px;padding:10px}
            QPushButton#advance {background:#f2d18b;color:#211f22;font-weight:800}
        """)
        layout = QVBoxLayout(self)
        heading = QLabel('🐒📜 让猴山的过去，真正决定未来')
        heading.setStyleSheet('font-size:22px;font-weight:900')
        layout.addWidget(heading)
        detail = QLabel('结案的历史会触发新事件。每次从两条道路中选择，'
                        '并逐幕阅读，第三幕后才结算资源和关系。'
                        '猴山法令和两只猴子之间的信任，还能解锁共同宪章。'
                        '\n不监视桌面、不自动弹窗；关闭或中断不会结算。')
        detail.setWordWrap(True)
        layout.addWidget(detail)
        self.event = QComboBox()
        for key, spec in LEGACY_EVENTS.items():
            self.event.addItem(spec.title, key)
        layout.addWidget(self.event)
        cast = QHBoxLayout()
        self.first = QComboBox()
        self.second = QComboBox()
        for i, pet in enumerate(colony.monkeys):
            label = f'#{i+1} {pet.display_name}'
            self.first.addItem(label, i)
            self.second.addItem(label, i)
        if colony.count > 1:
            self.second.setCurrentIndex(1)
        cast.addWidget(self.first)
        cast.addWidget(self.second)
        layout.addLayout(cast)
        self.route = QComboBox()
        self.route.addItem('协作', 'community')
        self.route.addItem('突破', 'elite')
        layout.addWidget(self.route)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(65)
        layout.addWidget(self.preview)
        self.scene = QLabel('🎬 等待开幕 · 未开始则不改变任何内容')
        self.scene.setWordWrap(True)
        self.scene.setMinimumHeight(100)
        self.scene.setStyleSheet('background:#293e56;border-radius:10px;padding:16px')
        layout.addWidget(self.scene)
        self.advance = QPushButton('🎭 开启第一幕')
        self.advance.setObjectName('advance')
        self.advance.clicked.connect(self.next_scene)
        layout.addWidget(self.advance)
        layout.addWidget(QLabel('📚 实时历史档案与事件解锁条件'))
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history, 1)
        footer = QHBoxLayout()
        cancel = QPushButton('⛔ 取消当前事件')
        cancel.clicked.connect(self.cancel_scene)
        refresh = QPushButton('↻ 更新史册')
        refresh.clicked.connect(self.refresh)
        close = QPushButton('关闭')
        close.clicked.connect(self.reject)
        for btn in (cancel, refresh, close):
            footer.addWidget(btn)
        layout.addLayout(footer)
        for widget in (self.event, self.route, self.first, self.second):
            widget.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_unused):
        journal = self.colony.expeditions
        laws = self.colony.laws
        bonds = self.colony.relationships
        a, b = self.first.currentData(), self.second.currentData()
        if journal is None:
            self.history.setPlainText('存档未初始化。')
            self.advance.setEnabled(False)
            return
        self.history.setPlainText(evolution_report(journal, laws, bonds, a, b))
        if self.plan is not None:
            return
        event_id = self.event.currentData()
        event = LEGACY_EVENTS[event_id]
        self.route.setItemText(0, event.choices[0])
        self.route.setItemText(1, event.choices[1])
        valid, reason = legacy_status(event_id, journal, laws, bonds, a, b)
        if a is None or b is None or a == b:
            valid, reason = False, '请先配置至少两只猴子并选择不同成员。'
        self.preview.setText(f'{event.intro}\n{reason}')
        self.advance.setEnabled(valid)
        self.advance.setText('🎭 开启第一幕')

    def next_scene(self):
        if self.plan is None:
            try:
                self.plan = prepare_evolution(
                    self.event.currentData(), self.route.currentData(),
                    self.colony.expeditions, self.colony.laws,
                    self.colony.relationships,
                    self.first.currentData(), self.second.currentData())
            except (ValueError, AttributeError) as exc:
                QMessageBox.information(self, '暂不能开启', str(exc))
                self.refresh()
                return
            self.scene_index = 0
            for widget in (self.event, self.route, self.first, self.second):
                widget.setEnabled(False)
        elif self.scene_index == 2:
            self.finish()
            return
        else:
            self.scene_index += 1
        self.scene.setText(f'第 {self.scene_index+1}/3 幕\n'
                           + self.plan.scenes[self.scene_index])
        self.advance.setText('✅ 完成并结算' if self.scene_index == 2 else '▶️ 下一幕')

    def finish(self):
        plan = self.plan
        if plan is None or self.scene_index != 2:
            return
        if not self.colony.expeditions.record_evolution(
                plan, self.colony.laws, self.colony.relationships):
            QMessageBox.warning(self, '结算失败',
                '解锁条件发生变化、事件已经完成、游戏资源不足或存档写入失败。'
                '本次没有发放任何奖励。')
            self.cancel_scene()
            return
        # Relation writes use the pre-existing relationship file. Like v0.17,
        # they follow an already-successful resource/history transaction.
        if self.colony.relationships is not None:
            try:
                if plan.route == 'community':
                    self.colony.relationships.record_shared_activity(plan.first, plan.second)
                    self.colony.relationships.record_shared_activity(plan.first, plan.second)
                else:
                    self.colony.relationships.record_collision(plan.first, plan.second)
            except OSError:
                QMessageBox.warning(self, '关系记录未完全保存',
                    '城市选择与资源已保存，但猴际关系文件写入失败。请检查本地存储空间。')
        self.scene.setText('📜 已载入猴山史册：' + LEGACY_EVENTS[plan.event_id].title +
                           '\n这次选择影响了后来的文明阶段。')
        self.cancel_scene(clear_text=False)

    def cancel_scene(self, *_unused, clear_text=True):
        self.plan = None
        self.scene_index = -1
        for widget in (self.event, self.route, self.first, self.second):
            widget.setEnabled(True)
        if clear_text:
            self.scene.setText('🎬 事件已取消，未结算奖励或人物关系。')
        self.refresh()
