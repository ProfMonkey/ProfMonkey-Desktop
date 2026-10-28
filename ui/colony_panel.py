"""Explicit opt-in local colony management; no windows/network introspection."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import Qt
from ui.character_render import render_mascot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QGridLayout,
     QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout)
from core.config import Settings
from core.profiles import PERSONALITIES, clean_profiles


class ColonyPanel(QDialog):
    def __init__(self, current: Settings, parent=None, asset_root: Path | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('🐒 猴山控制台 · ProfMonkey Desktop')
        self.resize(680, 710)
        self._asset_root = asset_root
        self._skin = current.skin
        self.setStyleSheet('''
          QDialog {background:#151923;color:#ffedcf} QLabel {color:#ffedcf}
          QLineEdit,QComboBox,QSpinBox {background:#282b3a;border:1px solid #525066;
            border-radius:8px;color:#fff0d7;padding:7px;min-height:22px}
          QPushButton {background:#373849;border:1px solid #595465;border-radius:10px;
            color:#fff0d7;padding:10px 12px;font-weight:650}
          QPushButton:hover {border-color:#f7c775} QPushButton#primary{background:#e9b85e;
            color:#211b1f;border-color:#e9b85e}
        ''')
        self.action = 'save'
        root = QVBoxLayout(self)
        title = QLabel('🐒 猴山管理局')
        title.setStyleSheet('font-size:23px;font-weight:850')
        root.addWidget(title)
        note = QLabel('养多少只？每只叫什么？爱研究还是爱捣蛋？\n这些设置仅保存在你的电脑上。')
        note.setStyleSheet('color:#b9b4c3');root.addWidget(note)
        self.count = QSpinBox()
        self.count.setRange(1, 6)
        self.count.setSuffix(' 只猴子')
        self.count.setValue(current.monkey_count)
        row = QHBoxLayout();row.addWidget(QLabel('猴子数量'));row.addWidget(self.count);row.addStretch()
        root.addLayout(row)
        self.names: list[QLineEdit] = []
        self.personalities: list[QComboBox] = []
        self.rows = []
        self.portraits = []
        profiles = clean_profiles(current.monkey_profiles)
        grid=QGridLayout()
        grid.setHorizontalSpacing(10);grid.setVerticalSpacing(7)
        grid.addWidget(QLabel('头像'),0,0);grid.addWidget(QLabel('编号'),0,1);grid.addWidget(QLabel('名字（最多12字）'),0,2)
        grid.addWidget(QLabel('性格'),0,3)
        for i in range(6):
            label = QLabel(f'#{i+1}')
            name = QLineEdit(profiles[i]['name']);name.setMaxLength(12)
            combo = QComboBox()
            for code, personality in PERSONALITIES.items():
                combo.addItem(personality,code)
            combo.setCurrentIndex(list(PERSONALITIES).index(profiles[i]['personality']))
            portrait = QLabel()
            portrait.setFixedSize(69,69)
            portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
            portrait.setStyleSheet('background:#2d4352;border-radius:10px')
            grid.addWidget(portrait,i+1,0)
            grid.addWidget(label,i+1,1)
            grid.addWidget(name,i+1,2)
            grid.addWidget(combo,i+1,3)
            self.portraits.append(portrait)
            self.names.append(name);self.personalities.append(combo)
            self.rows.append((portrait,label,name,combo))
            combo.currentIndexChanged.connect(lambda _i, index=i: self._update_portrait(index))
            self._update_portrait(i)
        root.addLayout(grid)
        self.count.valueChanged.connect(self._update_rows)
        self._update_rows(self.count.value())
        self.auto = QCheckBox('在猴山模式偶尔自动开会/抢香蕉（默认关闭）')
        self.auto.setChecked(current.social_enabled)
        root.addWidget(self.auto)
        hint = QLabel('注：见面会是独立窗口间同步播放的短剧，并非真实物理碰撞；\n专注期间不会触发，多猴不会监听键盘。')
        hint.setStyleSheet('color:#b9b4c3;font-size:12px');root.addWidget(hint)
        buttons = QHBoxLayout()
        for label, action in [('🍌 保存并抢香蕉','banana_duel'),('🗳 保存并开会','meeting')]:
            button=QPushButton(label);button.clicked.connect(lambda _, kind=action:self._finish(kind))
            buttons.addWidget(button)
        root.addLayout(buttons)
        footer=QHBoxLayout()
        cancel=QPushButton('取消');cancel.clicked.connect(self.reject)
        accept=QPushButton('保存配置');accept.setObjectName('primary')
        accept.clicked.connect(lambda:self._finish('save'))
        footer.addWidget(cancel);footer.addStretch();footer.addWidget(accept)
        root.addLayout(footer)

    def _update_portrait(self, index: int) -> None:
        if self._asset_root is None:
            return
        personality = self.personalities[index].currentData()
        transform = (Qt.TransformationMode.FastTransformation if self._skin == 'pixel'
                     else Qt.TransformationMode.SmoothTransformation)
        portrait = render_mascot(self._asset_root, personality, skin=self._skin).scaled(
            65,65,Qt.AspectRatioMode.KeepAspectRatio, transform)
        self.portraits[index].setPixmap(portrait)

    def _update_rows(self, count: int) -> None:
        for idx, widgets in enumerate(self.rows):
            for widget in widgets:
                widget.setEnabled(idx<count)

    def _finish(self, action: str) -> None:
        self.action=action
        self.accept()

    def updated(self, previous: Settings) -> Settings:
        profiles = [{'name': name.text(), 'personality': combo.currentData()}
                    for name, combo in zip(self.names, self.personalities)]
        return replace(previous,monkey_count=self.count.value(),
                       monkey_profiles=profiles,social_enabled=self.auto.isChecked()).validated()
