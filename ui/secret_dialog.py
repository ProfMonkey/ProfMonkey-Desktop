"""Manual-only hidden investigations of the six newly redesigned monkeys.

6 distinct mysteries, 3 chapters/3 desktop stages each, two branching routes.
No automatically opened story or new background polling. Discovery records are
counted from the user's explicit in-game gestures, never OS-level events.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)
from core.secrets import SECRET_CASES, ROUTE_NAMES, prepare_secret
from core.profiles import clean_profiles, PERSONALITIES


class SecretDialog(QDialog):
    def __init__(self,colony,parent=None):
        super().__init__(parent)
        self.colony=colony
        self.setWindowTitle('🗝️ 猴山隐藏事件簿 · 六猴六个秘密')
        self.resize(760,730)
        self.setStyleSheet('''
          QDialog{background:#101827;color:#fff0d9}
          QLabel{color:#fff0d9}
          QComboBox,QPlainTextEdit{background:#1b3044;color:#fff2dd;
            border:1px solid #57758c;border-radius:10px;padding:10px}
          QPushButton{background:#304a64;color:#fff2dd;
            border:1px solid #67869f;border-radius:10px;padding:11px}
          QPushButton#start{background:#f2d18a;color:#251d19;font-weight:900}
        ''')
        root=QVBoxLayout(self)
        title=QLabel('🔍 六只猴子，每只藏着一个秘密')
        title.setStyleSheet('font-size:24px;font-weight:900')
        root.addWidget(title)
        intro=QLabel(
            '🍌 投喂、快速戳、香蕉竞速、桌面镜子与既有城市历史都可能留下线索。'
            '\n每个秘密有3章，每章3幕；可以公开真相，也可以选择隐瞒。'
            '取消或中途打断不会结算。没有计时触发、自动弹窗或随机扣费。')
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.case=QComboBox()
        for case_id,info in SECRET_CASES.items():
            self.case.addItem(info['title'],case_id)
        root.addWidget(self.case)
        root.addWidget(QLabel('🐒 主角 / 证人（必须是两个不同的可见角色）'))
        names=clean_profiles(colony.primary.settings.monkey_profiles)
        row=QHBoxLayout()
        self.first=QComboBox();self.second=QComboBox()
        for i,pet in enumerate(colony.monkeys):
            label=f'#{i+1} {names[i]["name"]} · {PERSONALITIES[pet.personality]}'
            self.first.addItem(label,i)
            self.second.addItem(label,i)
        if colony.count>1:self.second.setCurrentIndex(1)
        row.addWidget(self.first);row.addWidget(self.second)
        root.addLayout(row)
        self.route=QComboBox()
        for key,title in ROUTE_NAMES.items():self.route.addItem(title,key)
        root.addWidget(self.route)
        self.preview=QLabel()
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(132)
        self.preview.setStyleSheet('background:#1a3449;border-radius:12px;padding:14px')
        root.addWidget(self.preview)
        self.start=QPushButton('🎬 在真实桌面上播放本章三幕')
        self.start.setObjectName('start')
        self.start.clicked.connect(self._start)
        root.addWidget(self.start)
        root.addWidget(QLabel('📂 档案碎片 · 线索与完成记录'))
        self.log=QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log,1)
        buttons=QHBoxLayout()
        cancel=QPushButton('⏹ 停止本章')
        cancel.clicked.connect(self._stop)
        reset=QPushButton('🧹 清空隐藏线索')
        reset.clicked.connect(self._clear)
        refresh=QPushButton('↻ 更新')
        refresh.clicked.connect(self.refresh)
        close=QPushButton('关闭')
        close.clicked.connect(self.accept)
        for button in (cancel,reset,refresh,close):buttons.addWidget(button)
        root.addLayout(buttons)
        self.case.currentIndexChanged.connect(self._case_changed)
        for widget in (self.first,self.second,self.route):
            widget.currentIndexChanged.connect(self.refresh)
        self._case_changed()

    def _case_changed(self,*_):
        # Favor the expected protagonist when selecting a new story.
        key=self.case.currentData()
        role=SECRET_CASES[key]['lead']
        who=next((i for i,pet in enumerate(self.colony.monkeys)
                  if pet.personality==role),None)
        if who is not None:
            self.first.setCurrentIndex(who)
            self.second.setCurrentIndex(0 if who!=0 else min(1,self.colony.count-1))
        self.refresh()

    def refresh(self,*_):
        journal=self.colony.secrets
        if journal is None:
            self.preview.setText('隐藏事件档案尚未绑定。')
            self.start.setEnabled(False)
            return
        key=self.case.currentData()
        meta=SECRET_CASES[key]
        row=journal.cases[key]
        items=[
            '🍌 投喂 '+str(journal.gestures['feeds'])+'/3 · '
            '💤 四连戳 '+str(journal.gestures['rapid_taps'])+'/2 · '
            '🏁 香蕉竞速 '+str(journal.gestures['races'])+'/1 · '
            '🪞 镜面互动 '+str(journal.gestures['mirrors'])+'/1',
        ]
        for entry in reversed(journal.news[-18:]):
            label=SECRET_CASES[entry['case']]['title']
            items.append(
                f'{label} · 第{entry["chapter"]}章 · '
                f'{ROUTE_NAMES[entry["route"]]}')
        final = journal.epilogue()
        if final is not None:
            items.insert(1, '\n🏆 六案全部结案 · 发现最终隐藏彩蛋：\n'+final+'\n')
        self.log.setPlainText('\n'.join(items))
        available,reason=journal.unlocked(
            key,self.colony.count,self.colony.primary.settings.monkey_profiles,
            self.colony.expeditions)
        if row['chapter']>=3:
            label='真相公开' if row['ending']=='unmasked' else '秘密留存'
            self.preview.setText(f'✅ {meta["title"]} 已完成所有三章。'
                f'\n永久结局：{label}。在本地档案里可以回看记录，不能重复领取章节。')
            self.start.setEnabled(False)
            return
        if not available:
            self.preview.setText(
                f'🔒 {meta["title"]}\n主角：{PERSONALITIES[meta["lead"]]}'
                f'\n解锁线索：{reason}\n不会自动播放；解锁后可主动选择两个角色。')
            self.start.setEnabled(False)
            return
        first,second=self.first.currentData(),self.second.currentData()
        try:
            plan=prepare_secret(journal,key,first,second,self.route.currentData(),
                self.colony.count,self.colony.primary.settings.monkey_profiles,
                self.colony.expeditions)
        except (ValueError,KeyError) as exc:
            self.preview.setText('🔑 已解锁，但当前演员不符合条件：\n'+str(exc))
            self.start.setEnabled(False)
            return
        chapter=meta['chapters'][plan.chapter]
        self.preview.setText(
            f'🗝️ 已解锁！{chapter[0]}\n'
            f'开场：{chapter[1]}\n'
            f'本章选择：{ROUTE_NAMES[plan.route]}'
            '\n将由当前选择的两只猴子在桌面上连续演出3幕。'
            '\n完整结束才会保存进度并影响两猴关系。')
        self.start.setEnabled(True)

    def _start(self):
        if self.colony.start_secret(self.case.currentData(),
                self.first.currentData(),self.second.currentData(),
                self.route.currentData()):
            self.accept()
            return
        QMessageBox.information(self,'猴山秘密尚未启动',
            '需要满足解锁条件，正确的主角与证人，且两只猴子空闲可见。'
            '\n暂停、专注、安静模式、拖动、其他短剧或竞速期间不能启动。')
        self.refresh()

    def _stop(self):
        self.colony.cancel_secret()
        self.refresh()

    def _clear(self):
        if self.colony.secrets is None:return
        ok=QMessageBox.question(self,'清除隐藏档案',
            '将永久清空此设备上全部6个秘密的章节进度及彩蛋计数。'
            '\n不会删除猴际关系或城市建设。确定继续？',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ok!=QMessageBox.StandardButton.Yes:return
        self.colony.cancel_secret()
        try:
            self.colony.secrets.clear()
        except OSError as exc:
            QMessageBox.warning(self,'无法写入本地档案',str(exc))
        self.refresh()
