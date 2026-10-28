"""Simple settings UI; no surprise permissions or startup persistence."""
from dataclasses import replace
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QPlainTextEdit, QSpinBox, QVBoxLayout)
from core.config import Settings


class SettingsDialog(QDialog):
    def __init__(self, current: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle('ProfMonkey 设置')
        self.resize(480, 520)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.mode = QComboBox()
        self.mode.addItem('安静模式（默认）','QUIET')
        self.mode.addItem('猴山模式（更多整活）','MONKEY')
        self.mode.setCurrentIndex(0 if current.mode == 'QUIET' else 1)
        self.size = QSpinBox(); self.size.setRange(90,240); self.size.setSingleStep(10); self.size.setValue(current.size)
        self.count = QSpinBox(); self.count.setRange(1,6); self.count.setValue(current.monkey_count); self.count.setSuffix(' 只')
        self.count.setToolTip('每只都有独立的运动和表情；4～6 只可能增加电脑负担')
        self.quiet = QSpinBox(); self.quiet.setRange(90,3600); self.quiet.setSuffix(' 秒'); self.quiet.setValue(current.quiet_interval)
        self.monkey = QSpinBox(); self.monkey.setRange(40,1800); self.monkey.setSuffix(' 秒'); self.monkey.setValue(current.monkey_interval)
        self.sound = QCheckBox('启用少量音效'); self.sound.setChecked(current.sound)
        self.stories = QCheckBox('允许自动触发小事故'); self.stories.setChecked(current.stories)
        self.history = QCheckBox('本地收藏已完成事件（默认关闭）'); self.history.setChecked(current.history)
        self.social = QCheckBox('猴山模式中偶发联合短剧（至少两只，默认关闭）'); self.social.setChecked(current.social_enabled)
        self.ambient = QCheckBox('猴山模式中自动碰面打招呼 / 争论（至少两只，默认关闭）')
        self.ambient.setChecked(current.ambient_encounters)
        self.progress = QCheckBox('启用本地猴学勋章（只统计猴子互动；默认关闭）')
        self.progress.setChecked(current.progress_enabled)
        self.quotes = QPlainTextEdit()
        self.quotes.setPlaceholderText('每行一句，例如：宇宙很大，猴子很忙。')
        self.quotes.setPlainText('\n'.join(current.custom_quotes))
        self.quotes.setFixedHeight(82)
        self.top = QCheckBox('窗口始终置顶'); self.top.setChecked(current.always_on_top)
        self.skin = QComboBox()
        for label, code in [('教授猴','professor'),('熬夜猴','night'),('西装猴','suit'),('考试周猴','exam'),('Pixel Art','pixel')]:
            self.skin.addItem(label,code)
            if code == current.skin:
                self.skin.setCurrentIndex(self.skin.count()-1)
        form = QFormLayout()
        form.addRow('模式',self.mode); form.addRow('🐒 猴子数量',self.count); form.addRow('猴子大小',self.size)
        form.addRow('安静模式事故间隔',self.quiet); form.addRow('猴山模式事故间隔',self.monkey)
        form.addRow('角色配色',self.skin)
        layout = QVBoxLayout(self); layout.addLayout(form)
        layout.addWidget(QLabel('自定义猴学语录（最多 12 句，菜单中随机展示）'))
        layout.addWidget(self.quotes)
        for widget in (self.stories,self.social,self.ambient,self.history,self.progress,self.top,self.sound):
            layout.addWidget(widget)
        label = QLabel('隐私：完全离线，不录屏、不读取键盘或剪贴板；无开机自启。\n当前音效为实验性：不包含后台输入监听。')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def value(self, previous: Settings) -> Settings:
        return replace(previous,mode=self.mode.currentData(),size=self.size.value(),
                       monkey_count=self.count.value(),
                       quiet_interval=self.quiet.value(),monkey_interval=self.monkey.value(),
                       stories=self.stories.isChecked(),social_enabled=self.social.isChecked(),
                       ambient_encounters=self.ambient.isChecked(),history=self.history.isChecked(),
                       always_on_top=self.top.isChecked(),sound=self.sound.isChecked(),skin=self.skin.currentData(),
                       progress_enabled=self.progress.isChecked(),
                       custom_quotes=self.quotes.toPlainText().splitlines()).validated()
