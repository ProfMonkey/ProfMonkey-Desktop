"""Native Qt city case files: branches, cast selection and three-chapter history."""
from __future__ import annotations
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)
from core.city_life import (CASE_TITLES, CASE_CHAPTERS, CASE_CHOICES,
                            prepare_city_case)


class CityLifeDialog(QDialog):
    def __init__(self, colony, selected_case: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.colony = colony
        self.setWindowTitle('📰 活着的猴山 · 城市连续事件')
        self.resize(690, 630)
        self.setStyleSheet('''
          QDialog {background:#131e31;color:#ffeed3}
          QLabel {color:#ffeed3}
          QComboBox,QPlainTextEdit {background:#24334c;color:#ffeece;
            border:1px solid #61738e;border-radius:11px;padding:10px}
          QPushButton {background:#41526e;color:#ffeed3;
            border:1px solid #647693;border-radius:11px;padding:11px}
          QPushButton#start {background:#f6d18d;color:#251f1e;font-weight:900}
        ''')
        layout = QVBoxLayout(self)
        heading = QLabel('📰 猴山大事件 · 一座城市自己的历史')
        heading.setStyleSheet('font-size:22px;font-weight:900')
        layout.addWidget(heading)
        intro = QLabel('只有已经建成的建筑才能开启对应案件。'
                       '每个案件有3章，每章3幕，至少两只空闲猴子参与。'
                       '\n一次选择会改变猴际关系、资源，以及最终结局。'
                       '被打断或尚未演完的场景不会更新档案。')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(QLabel('🏛️ 选择一座已建城市的案卷'))
        self.case = QComboBox()
        for key, title in CASE_TITLES.items():
            self.case.addItem(title, key)
        if selected_case in CASE_TITLES:
            self.case.setCurrentIndex(list(CASE_TITLES).index(selected_case))
        layout.addWidget(self.case)
        layout.addWidget(QLabel('🐒 选择两个出场角色'))
        people = QHBoxLayout()
        self.first = QComboBox()
        self.second = QComboBox()
        for i, pet in enumerate(colony.monkeys):
            label = f'#{i+1} {pet.display_name} · {pet.personality}'
            self.first.addItem(label, i)
            self.second.addItem(label, i)
        if colony.count > 1:
            self.second.setCurrentIndex(1)
        people.addWidget(self.first)
        people.addWidget(self.second)
        layout.addLayout(people)
        layout.addWidget(QLabel('⚖️ 这次调查怎样行动？'))
        self.choice = QComboBox()
        self.choice.addItem('谨慎路线', 'careful')
        self.choice.addItem('大胆路线', 'bold')
        layout.addWidget(self.choice)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(96)
        self.preview.setStyleSheet('background:#26384e;border-radius:12px;padding:14px;')
        layout.addWidget(self.preview)
        self.start_button = QPushButton('▶️ 演出本章三幕事件')
        self.start_button.setObjectName('start')
        self.start_button.clicked.connect(self._launch)
        layout.addWidget(self.start_button)
        layout.addWidget(QLabel('🗞️ 猴山历史档案 · 最近章节'))
        self.paper = QPlainTextEdit()
        self.paper.setReadOnly(True)
        layout.addWidget(self.paper, 1)
        bottom = QHBoxLayout()
        refresh = QPushButton('⟳ 刷新城市档案')
        refresh.clicked.connect(self.refresh)
        stop = QPushButton('⏹ 取消当前章节')
        stop.clicked.connect(self._stop)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        bottom.addWidget(refresh)
        bottom.addWidget(stop)
        bottom.addWidget(close)
        layout.addLayout(bottom)
        for widget in (self.case,self.first,self.second,self.choice):
            widget.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_args):
        journal = self.colony.expeditions
        if journal is None:
            self.preview.setText('本地探险档案还没有初始化。')
            self.start_button.setEnabled(False)
            return
        case_id = self.case.currentData()
        state = journal.city_cases[case_id]
        title = CASE_TITLES[case_id]
        options = CASE_CHOICES[case_id]
        descriptions = dict(zip(('careful','bold'), options))
        for i, route in enumerate(('careful','bold')):
            self.choice.setItemText(i, descriptions[route])
        news = []
        for row in reversed(journal.city_news[-15:]):
            name = CASE_TITLES[row['case']]
            outcome = (' · 达成和解' if row['ending']=='reconciled' else
                       ' · 留下争议' if row['ending']=='chaos' else '')
            news.append(f'{name} · 第{row["chapter"]}章完成 · '
                        f'{"谨慎" if row["choice"]=="careful" else "大胆"}{outcome}')
        self.paper.setPlainText('\n'.join(news) if news
                                else '城市刚刚建成，尚未发生需要猴子共同解决的事件。')
        if case_id not in journal.buildings:
            self.preview.setText(f'🔒 {title} 还不能启动。'
                                 '\n必须先用探险资源建造对应城市建筑。')
            self.start_button.setEnabled(False)
            return
        if state['chapter']==3:
            ending = ('温暖和解' if state['ending']=='reconciled' else '混乱未解')
            self.preview.setText(
                f'✅ {title} 已全三章结案：{ending}。'
                '\n档案保留在本地，不能反复领取相同的章节奖励。')
            self.start_button.setEnabled(False)
            return
        first, second = self.first.currentData(),self.second.currentData()
        if first==second or first is None or second is None:
            self.preview.setText('请挑选两位不同的猴子。')
            self.start_button.setEnabled(False)
            return
        rel = self.colony.relationships.get(first,second) if self.colony.relationships else {}
        try:
            plan=prepare_city_case(case_id,state,first,second,
                 self.choice.currentData(),
                 bond=rel.get('bond',0),trust=rel.get('trust',0))
        except ValueError:
            self.preview.setText('当前章节或行动方式无效。')
            self.start_button.setEnabled(False)
            return
        chapter=CASE_CHAPTERS[case_id][plan.chapter]
        delta=plan.resource_delta
        extra = ('；结局预览：' +
                 ('和解' if plan.ending=='reconciled' else '留下争议')
                 if plan.ending is not None else '')
        self.preview.setText(
            f'{chapter[0]}\n{chapter[1]}\n本章选择：'
            f'{descriptions[plan.choice]}\n结算后资源变化 '
            f'🍌{delta[0]:+d} / 🔬{delta[1]:+d} / ⭐{delta[2]:+d}'
            f'{extra}\n尚未演完三幕前，不扣除也不奖励任何资源。')
        self.start_button.setEnabled(True)

    def _launch(self):
        if self.colony.start_city_life(self.case.currentData(),
                self.first.currentData(), self.second.currentData(),
                self.choice.currentData()):
            self.accept()
            return
        QMessageBox.information(self, '城市事件暂不可用',
            '需要已建成建筑、未结案的章节和两只空闲可见猴子。'
            '\n暂停、拖动、其他剧情、探险、议会或专注期间无法启动。')

    def _stop(self):
        self.colony.cancel_city_life()
        self.refresh()
