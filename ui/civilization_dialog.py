"""Native Qt pixel-style city builder; no binary assets or networking."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)
from core.civilization import (BUILDINGS, RESOURCE_LABELS, city_report,
                               city_tier, construction_status)
from ui.city_life_dialog import CityLifeDialog


class CityMapWidget(QWidget):
    """Draw four pixel-style plots from a persistent local construction state."""

    def __init__(self, journal, parent=None):
        super().__init__(parent)
        self.journal = journal
        self.setMinimumHeight(245)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor('#142337'))
        painter.fillRect(0, int(h*.62), w, h, QColor('#32505c'))
        for n in range(15):
            painter.fillRect((n*97+31) % max(1, w),
                             (n*37+18) % max(1, int(h*.48)), 3, 3,
                             QColor('#f7d391'))
        painter.setBrush(QColor('#f1cc80'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(max(0, w-80), 22, 36, 36)
        gap = 8
        tile_w = max(1, (w-28-gap*3)//4)
        tile_h = 130
        for idx, key in enumerate(BUILDINGS):
            owned = key in self.journal.buildings
            x, y = 14+idx*(tile_w+gap), h-tile_h-20
            painter.fillRect(x, y, tile_w, tile_h,
                             QColor('#354b63') if owned else QColor('#162034'))
            painter.setPen(QPen(QColor('#f4d18b') if owned
                                else QColor('#657590'), 2))
            painter.drawRect(x, y, tile_w, tile_h)
            center = x+tile_w//2
            if owned:
                bh = (43, 65, 50, 83)[idx]
                color = ('#c49d5f','#79b3d4','#a3b996','#e4c988')[idx]
                ww = min(45, tile_w*2//3)
                painter.fillRect(center-ww//2, y+tile_h-30-bh,
                                 ww, bh, QColor(color))
                painter.fillRect(center-3, y+tile_h-42, 7, 34,
                                 QColor('#243449'))
                painter.fillRect(center-4, y+tile_h-33-bh, 8, 12,
                                 QColor('#f6d58e'))
            else:
                painter.setPen(QColor('#99adc3'))
                painter.setFont(QFont('Microsoft YaHei UI', 22, QFont.Weight.Bold))
                painter.drawText(x, y+7, tile_w, tile_h-38,
                                 Qt.AlignmentFlag.AlignCenter, '＋')
            painter.setFont(QFont('Microsoft YaHei UI', 9))
            painter.setPen(QColor('#f8e8cb'))
            label = ('香蕉仓库','银河望远镜','公共广场','联合实验室')[idx]
            painter.drawText(x+2, y+tile_h-28, tile_w-4, 25,
                             Qt.AlignmentFlag.AlignCenter, label)
        level, title = city_tier(self.journal.buildings)
        painter.setPen(QColor('#ffe0a4'))
        painter.setFont(QFont('Microsoft YaHei UI', 11, QFont.Weight.Bold))
        painter.drawText(11, 7, w-22, 26,
                         Qt.AlignmentFlag.AlignLeft, f'猴山文明 {level}/4 · {title}')


class CivilizationDialog(QDialog):
    def __init__(self, colony, parent=None):
        super().__init__(parent)
        self.colony = colony
        self.setWindowTitle('🏗️ 猴山文明 · 建造与发展')
        self.resize(790, 750)
        self.setStyleSheet('''
          QDialog {background:#141d2f;color:#fff0d2}
          QLabel {color:#fff0d2}
          QComboBox {background:#26344d;color:#fff0d2;
            border:1px solid #63738f;border-radius:11px;padding:9px}
          QPushButton {background:#3e4d69;color:#ffeed0;
            border:1px solid #647693;border-radius:11px;padding:11px}
          QPushButton#build {background:#f4cd82;color:#28201b;font-weight:850}
        ''')
        layout = QVBoxLayout(self)
        heading = QLabel('🏗️ 猴山文明 · 用探险所得建立城市')
        heading.setStyleSheet('font-size:21px;font-weight:900')
        layout.addWidget(heading)
        info = QLabel('消耗虚构香蕉、科研点和声望完成建筑，'
                      '建好的建筑会增强后续探险。\n'
                      '建筑和余额在同一份本地存档里同时更新，不会影响真实电脑。')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.map = CityMapWidget(colony.expeditions)
        layout.addWidget(self.map)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet('background:#1e2b40;padding:12px;border-radius:10px')
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('🔨 选择要建造的建筑'))
        self.selection = QComboBox()
        for key, spec in BUILDINGS.items():
            self.selection.addItem(spec.title, key)
        self.selection.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.selection)
        self.details = QLabel()
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        self.build_button = QPushButton('🔨 建造（扣除资源）')
        self.build_button.setObjectName('build')
        self.build_button.clicked.connect(self.build)
        self.show_button = QPushButton('🖥 放到桌面')
        self.show_button.clicked.connect(self.display)
        self.story_button = QPushButton('🗞️ 查看本建筑连续事件')
        self.story_button.clicked.connect(self.open_story)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        actions.addWidget(self.build_button)
        actions.addWidget(self.show_button)
        actions.addWidget(self.story_button)
        actions.addWidget(close)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self, *_args):
        journal = self.colony.expeditions
        self.summary.setText(city_report(journal.buildings,
                                         journal.resources, journal.city_cases))
        key = self.selection.currentData()
        spec = BUILDINGS[key]
        eligible, reason = construction_status(key, journal.resources,
                                                journal.buildings)
        cost = ' / '.join(f'{label} × {n}' for label, n in
                         zip(RESOURCE_LABELS, spec.cost) if n)
        self.details.setText(f'{spec.description}\n费用：{cost}\n{reason}')
        self.build_button.setEnabled(eligible)
        self.show_button.setEnabled(key in journal.buildings)
        self.story_button.setEnabled(key in journal.buildings)
        self.map.update()

    def build(self):
        key = self.selection.currentData()
        spec = BUILDINGS.get(key)
        if spec is None:
            return
        price = '、'.join(f'{label} {amount}' for label, amount in
                         zip(RESOURCE_LABELS, spec.cost) if amount)
        if QMessageBox.question(self, '确认建造',
                f'确定建设 {spec.title} 吗？\n这会扣除虚构资源：{price}。'
                ) != QMessageBox.StandardButton.Yes:
            return
        if not self.colony.expeditions.construct(key):
            QMessageBox.warning(self, '建造失败',
                '资源不足、基础建筑未完成，或本地存档无法安全写入。')
        self.refresh()

    def display(self):
        if not self.colony.display_city_building(self.selection.currentData()):
            QMessageBox.information(self, '无法展示',
                '请先建造建筑；桌面最多同时展示8件道具。')

    def open_story(self):
        """Use the same verified building ownership as the casebook."""
        key = self.selection.currentData()
        if key not in self.colony.expeditions.buildings:
            return
        CityLifeDialog(self.colony, key, self).exec()
        self.refresh()
