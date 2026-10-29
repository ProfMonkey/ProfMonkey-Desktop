"""v0.22 original six-character studio: real live SVG rigs, 13 actions.

All six rendered with the same runtime QtSvg pipeline as the desktop pets.
The art gallery runs ONLY when opened; the timer stops on close.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)
from core.profiles import PERSONALITIES, clean_profiles
from ui.character_render import render_mascot


class CharacterGallery(QDialog):
    def __init__(self, colony, parent=None):
        super().__init__(parent)
        self.colony = colony
        self._cache: dict[tuple[str,str,int],object] = {}
        self._frame = 0
        self.setWindowTitle('🎨 ProfMonkey 六猴角色设计中心 · v0.22')
        self.resize(910, 780)
        self.setStyleSheet('''
            QDialog{background:#101A29;color:#FFF2D9}
            QLabel{color:#FFF2D9}
            QComboBox,QPushButton{background:#263A52;color:#FFF2D9;
                border:1px solid #6A8096;border-radius:9px;padding:9px}
            QPushButton:hover{border-color:#F4CD7B}
        ''')
        main = QVBoxLayout(self)
        title = QLabel('六种身形 · 六套服装 · 六种性格')
        title.setStyleSheet('font-size:26px;font-weight:900')
        main.addWidget(title)
        sub = QLabel('全新原创角色：缩小头部、补足躯干与四肢，统一轮廓与落地锚点。\n'
                     '下面的猴子是运行时真正绘制的角色，不是 AI 宣传画。')
        sub.setWordWrap(True)
        sub.setStyleSheet('color:#ADBACD')
        main.addWidget(sub)
        self.action = QComboBox()
        self.action.addItems(['idle','blink','walk','turn','sleep','wake','run',
                              'eat_banana','angry','slip','fall','get_up','dragged'])
        self.action.currentTextChanged.connect(self.restart)
        selector = QHBoxLayout()
        selector.addWidget(QLabel('选择动作：'))
        selector.addWidget(self.action)
        main.addLayout(selector)
        grid = QGridLayout()
        self.frames = []
        descriptions = [
            '🎓 学术研究 · 花呢外套与书卷',
            '🍌 香蕉恶作剧 · 深色兜帽与香蕉袋',
            '💤 摸鱼大师 · 连帽衫与耳机',
            '🧪 疯狂发明 · 护目镜与试管',
            '🧭 猴山指挥 · 红色制服与规划书',
            '🌱 安静观察 · 绿色套衫与随身读物',
        ]
        profiles = clean_profiles(colony.primary.settings.monkey_profiles)
        for i, persona in enumerate(PERSONALITIES):
            card = QWidget(self)
            card.setStyleSheet('background:#1B2D40;border:1px solid #456078;border-radius:12px')
            box = QVBoxLayout(card)
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedHeight(185)
            label.setStyleSheet('background:transparent;border:none')
            box.addWidget(label)
            name = QLabel(f'{i+1:02} · {profiles[i]["name"]} · {PERSONALITIES[persona]}')
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet('font-size:15px;font-weight:800;border:none')
            box.addWidget(name)
            description = QLabel(descriptions[i])
            description.setWordWrap(True)
            description.setAlignment(Qt.AlignmentFlag.AlignCenter)
            description.setStyleSheet('color:#C6D5DB;border:none')
            box.addWidget(description)
            grid.addWidget(card,i//3,i%3)
            self.frames.append((label,persona))
        main.addLayout(grid)
        close = QPushButton('关闭设计中心')
        close.clicked.connect(self.accept)
        main.addWidget(close)
        self.timer = QTimer(self)
        self.timer.setInterval(160)
        self.timer.timeout.connect(self.advance)
        self.advance()
        self.timer.start()

    def restart(self, *_):
        self._frame = 0
        self.advance()

    def advance(self):
        action = self.action.currentText()
        count = len(self.colony.primary.player.specs[action].frames)
        step = self._frame % count
        root = self.colony.primary._art_root
        for label,persona in self.frames:
            key=(persona,action,step)
            if key not in self._cache:
                if len(self._cache)>240:
                    self._cache.clear()
                self._cache[key] = render_mascot(root,persona,action,step,count).scaled(
                    170,170,Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(self._cache[key])
        self._frame += 1

    def reject(self):
        self.timer.stop()
        super().reject()

    def accept(self):
        self.timer.stop()
        super().accept()
