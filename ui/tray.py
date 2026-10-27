"""Persistent pause/exit/settings/story controls via character and system tray."""
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QIcon, QDesktopServices
from PySide6.QtWidgets import (QApplication, QFileDialog, QInputDialog, QMenu,
    QMessageBox, QSystemTrayIcon, QDialog)
from ui.overlay import MonkeyOverlay
from ui.colony import MonkeyColony
from ui.colony_dialog import MonkeyCountDialog
from ui.colony_panel import ColonyPanel
from ui.settings_dialog import SettingsDialog
from ui.dashboard import Dashboard
from core.focus import format_seconds
from core.config import ConfigStore
from core.relationships import RelationshipStore
from core.quests import QuestBoard
from core.chronicle import ChronicleStore
from ui.chronicle_dialog import ChronicleDialog
from ui.council_dialog import CouncilDialog
from core.governance import MonkeyLaws
from ui.law_dialog import MonkeyLawDialog
from core.expeditions import ExpeditionJournal
from ui.expedition_dialog import ExpeditionDialog
from ui.civilization_dialog import CivilizationDialog
from ui.city_life_dialog import CityLifeDialog
from ui.evolution_dialog import EvolutionDialog
from ui.society_dialog import SocietyDialog
from core.story_card import STORIES, render_story_card
from ui.relationship_dialog import RelationshipDialog
from ui.quest_dialog import QuestDialog


class MonkeyTray:
    def __init__(self, app: QApplication, overlay: MonkeyOverlay, icon: QIcon,
                 config: ConfigStore | None = None, manifest: Path | None = None,
                 site_path: Path | None = None,
                 colony: MonkeyColony | None = None) -> None:
        self.app, self.overlay = app, overlay
        self.colony = colony or MonkeyColony(overlay, overlay._art_root / "idle.png", manifest)
        self.target = overlay
        self.config = config or ConfigStore()
        self.relationships = RelationshipStore(self.config.folder / 'relationships.json')
        self.quests = QuestBoard(self.config.folder / 'daily_quests.json')
        self.chronicle = ChronicleStore(self.config.folder / 'chronicle.json',
                                        enabled=overlay.settings.chronicle_enabled)
        self.laws = MonkeyLaws(self.config.folder / 'monkey_laws.json')
        self.expeditions = ExpeditionJournal(self.config.folder / 'expeditions.json')
        self.colony.relationships = self.relationships
        self.colony.quests = self.quests
        self.colony.chronicle = self.chronicle
        self.colony.laws = self.laws
        self.colony.expeditions = self.expeditions
        self.colony._refresh_civic(force=True)
        self.manifest = manifest
        self.site_path = site_path
        self.menu = QMenu(overlay)
        self.show_action = self.menu.addAction('🐒 显示所有猴子', self.restore)
        self.hide_action = self.menu.addAction('🙈 隐藏所有猴子', self.colony.hide_all)
        self.menu.addAction('🏠 召集所有猴子回家', self.reset_position)
        self.count_action = self.menu.addAction('', self.choose_count)
        self.refresh_count_label()
        self.menu.addAction('🎨 六猴全新造型 · 各有独立角色设计', self.show_character_lineup)
        self.menu.addAction('🎛 猴山管理局 · 名字与性格', self.open_colony_panel)
        self.menu.addAction('🤝 猴山关系档案 · 好友/死对头/师徒', self.open_relationships)
        self.menu.addAction('📜 今日猴山任务 · 猴学积分', self.show_quests)
        self.menu.addAction('📖 猴山纪事 · 连续剧情/成长', self.show_chronicle)
        self.menu.addAction('🗳 猴山议会 · 三猴投票与合作网络', self.open_council)
        self.menu.addAction('📜 猴山自治 · 法令与火箭试飞', self.show_laws)
        self.menu.addAction('🧭 猴山探险局 · 小队与日报', self.show_expeditions)
        self.menu.addAction('🏗️ 猴山文明 · 四座建筑与城市发展', self.show_civilization)
        self.menu.addAction('🗞️ 活着的猴山 · 四大城市连续事件', lambda: self.show_city_life())
        self.menu.addAction('📜 猴山历史 · 文明演化与新事件', self.show_evolution)
        self.menu.addAction('🏛️ 猴山自主社会 · 岗位/阵营/互动', self.show_society)
        self.menu.addAction('⛔ 停止当前城市章节', self.colony.cancel_city_life)
        self.menu.addAction('⛔ 停止猴山探险', self.colony.cancel_expedition)
        self.chronicle_action = self.menu.addAction('📖 记录猴山纪事（默认关）')
        self.chronicle_action.setCheckable(True)
        self.chronicle_action.setChecked(overlay.settings.chronicle_enabled)
        self.chronicle_action.toggled.connect(self.set_chronicle_enabled)
        furniture_menu = self.menu.addMenu('🛋 猴山家具与道具')
        for kind, label in [('banana_tree','🍌 放置香蕉树'),('blackboard','📋 放置猴学黑板'),
                            ('trampoline','🛝 放置蹦床'),('chair','🪑 放置教授椅'),('mirror','🪞 放置猴山镜子')]:
            furniture_menu.addAction(label, lambda checked=False, value=kind: self.place_furniture(value))
        furniture_menu.addSeparator()
        furniture_menu.addAction('收起所有家具', self.colony.clear_furniture)
        group_menu = self.menu.addMenu('🐾 猴山行动与物理互动')
        behavior_menu = group_menu.addMenu('群体行动方式')
        behavior_group = QActionGroup(behavior_menu)
        behavior_group.setExclusive(True)
        self.behavior_actions = {}
        for code, label in [('free', '自由生活：各自散步'), ('follow', '跟随猴教授：排队移动')]:
            action = QAction(label, behavior_menu)
            action.setCheckable(True)
            action.setChecked(overlay.settings.colony_behavior == code)
            behavior_group.addAction(action)
            behavior_menu.addAction(action)
            action.triggered.connect(lambda checked=False, value=code: self.set_colony_behavior(value))
            self.behavior_actions[code] = action
        self.collision_action = group_menu.addAction('🤜 允许猴子身体碰撞')
        self.collision_action.setCheckable(True)
        self.collision_action.setChecked(overlay.settings.collisions_enabled)
        self.collision_action.toggled.connect(self.set_collisions_enabled)
        self.ambient_action = group_menu.addAction('💬 自动碰面：偶尔打招呼/争论')
        self.ambient_action.setCheckable(True)
        self.ambient_action.setChecked(overlay.settings.ambient_encounters)
        self.ambient_action.toggled.connect(self.set_ambient_encounters)
        self.civic_action = group_menu.addAction('🏛️ 自主社会 · 历史影响猴子日常')
        self.civic_action.setCheckable(True)
        self.civic_action.setChecked(overlay.settings.civic_autonomy)
        self.civic_action.toggled.connect(self.set_civic_autonomy)
        group_menu.addAction('🎭 让附近两只猴子互动一次', self.demo_encounter)
        group_menu.addAction('🧪 指定两只猴子上演双幕短剧', self.choose_duo_pair)
        group_menu.addAction('🍌 放置公共香蕉 · 猴子竞速', self.drop_shared_banana)
        social = self.menu.addMenu('🤝 猴子之间的互动')
        social.addAction('🗳 召集猴学委员会',lambda:self.launch_social('meeting'))
        social.addAction('🍌 香蕉争夺战',lambda:self.launch_social('banana_duel'))
        social.addAction('停止联合短剧',self.colony.cancel_social)
        self.menu.addAction('📸 猴山合照 · 导出 PNG', self.export_portrait)
        self.menu.addSeparator()
        mode_menu = self.menu.addMenu('行为模式')
        group = QActionGroup(mode_menu)
        group.setExclusive(True)
        self.mode_actions = {}
        for code, title in [('QUIET','安静模式'),('MONKEY','🐒 猴山模式')]:
            action = QAction(title,mode_menu)
            action.setCheckable(True)
            action.setChecked(overlay.settings.mode==code)
            group.addAction(action); mode_menu.addAction(action)
            action.triggered.connect(lambda checked=False, m=code:self.set_mode(m))
            self.mode_actions[code] = action
        self.pause_action = self.menu.addAction('⏸ 暂停猴子')
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self.colony.toggle_pause)
        self.menu.addSeparator()
        self.menu.addAction('🍌 投喂当前猴子', self.feed_target)
        self.menu.addAction('💬 让当前猴子讲猴学', lambda: self.target.say_quote())
        self.menu.addAction('🏅 猴学档案 / 勋章', self.show_dashboard)
        focus_menu = self.menu.addMenu('📚 陪你专注（完全本地）')
        self.focus_actions = {}
        for minutes in (15, 25, 45, 60):
            focus_menu.addAction(f'开始专注 {minutes} 分钟',
                                 lambda checked=False, m=minutes:self.start_focus(m))
        focus_menu.addSeparator()
        self.focus_pause = focus_menu.addAction('暂停专注', self.toggle_focus_pause)
        focus_menu.addAction('查看剩余时间', self.show_focus_status)
        self.focus_cancel = focus_menu.addAction('结束专注', self.cancel_focus)
        self.menu.addSeparator()
        story_menu = self.menu.addMenu('🎭 立即上演')
        story_menu.addAction('停止当前事故',self.stop_story)
        story_menu.addAction('🎲 随机来一段', self.random_story)
        story_menu.addSeparator()
        for name,title in [('banana','🍌 香蕉事故'),('blackboard','教授的尊严'),('mirror','镜像事故'),
                           ('keyboard','键盘暴走（手动演示）'),('edge','边缘坠落')]:
            story_menu.addAction(title,lambda checked=False, event=name:self.start_story(event))
        actions = self.menu.addMenu('🎬 手动预览动作')
        names = {'idle':'待机','blink':'眨眼','walk':'走路','run':'跑步','turn':'转身',
                 'sleep':'睡觉','wake':'醒来','eat_banana':'吃香蕉','slip':'滑倒',
                 'fall':'摔倒','get_up':'爬起','angry':'生气','dragged':'拖动'}
        for key,label in names.items():
            actions.addAction(label,lambda checked=False, name=key:self.play_once(name))
        self.demo_action = self.menu.addAction('循环预览全部动作（调试）')
        self.demo_action.setCheckable(True)
        self.demo_action.toggled.connect(overlay.toggle_demo)
        self.menu.addSeparator()
        self.topmost_action = self.menu.addAction('始终置顶')
        self.topmost_action.setCheckable(True)
        self.topmost_action.setChecked(overlay.settings.always_on_top)
        self.topmost_action.toggled.connect(self.set_topmost)
        self.menu.addAction('⚙ 设置',self.edit_settings)
        self.menu.addAction('🌌 关于 ProfMonkey · 介绍页面',self.open_intro)
        self.menu.addAction('🎞 导出动作 GIF（不录屏）',self.export_gif)
        self.menu.addAction('📽 导出猴学短剧 GIF（不录屏）',self.export_story)
        self.menu.addAction('🪪 导出猴山故事卡 PNG', self.export_story_card)
        self.menu.addAction('📁 查看本地事件收藏',self.show_history)
        self.menu.addAction('清空本地事件收藏',self.clear_history)
        self.menu.addSeparator()
        self.menu.addAction('❌ 退出 ProfMonkey',self.quit)
        self.colony.bind_menu(self.menu, self.select_target)
        self.colony.bind_city_story(self.show_city_life)
        self.tray = QSystemTrayIcon(icon,overlay)
        self.tray.setToolTip('ProfMonkey Desktop · v0.20 six original monkey mascots')
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.has_tray = QSystemTrayIcon.isSystemTrayAvailable()
        self._focus_timer = QTimer(overlay)
        self._focus_timer.setInterval(4000)
        self._focus_timer.timeout.connect(self.update_focus_ui)
        self._focus_timer.start()
        self.update_focus_ui()
        if self.has_tray:
            self.tray.show()
        else:
            self.hide_action.setEnabled(False)
            self.hide_action.setToolTip('无系统托盘，隐藏后可能无法恢复')

    def update_focus_ui(self) -> None:
        focus = self.overlay.focus
        self.focus_pause.setEnabled(focus.active)
        self.focus_cancel.setEnabled(focus.active)
        self.focus_pause.setText('继续专注' if focus.state == 'paused' else '暂停专注')
        tip = f'ProfMonkey Desktop · {self.colony.count} 只猴子'
        if focus.active:
            tip += f' · 专注 {format_seconds(focus.remaining())}'
            if focus.state == 'paused':
                tip += '（暂停）'
        self.tray.setToolTip(tip)

    def start_focus(self, minutes: int) -> None:
        if self.overlay.focus.active:
            reply = QMessageBox.question(None, '重新开始专注', '当前专注未结束。确定重新计时吗？')
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.overlay.start_focus(minutes)
        self.colony.prepare_focus()
        self.update_focus_ui()

    def toggle_focus_pause(self) -> None:
        if self.overlay.focus.state == 'running':
            self.overlay.focus.pause()
            self.overlay._say('暂停一下也没关系。')
        elif self.overlay.focus.state == 'paused':
            self.overlay.focus.resume()
            self.overlay._say('继续专注，教授在旁边！')
        self.update_focus_ui()

    def cancel_focus(self) -> None:
        self.overlay.focus.cancel()
        self.overlay._say('专注已结束。')
        self.update_focus_ui()

    def show_focus_status(self) -> None:
        focus = self.overlay.focus
        if focus.active:
            status = '已暂停' if focus.state == 'paused' else '进行中'
            message = f'{status} · 还剩 {format_seconds(focus.remaining())}'
        elif focus.state == 'completed':
            message = '本次专注已完成！'
        else:
            message = '目前没有专注任务。'
        QMessageBox.information(None, '🐒 教授陪你专注', message)

    def show_dashboard(self) -> None:
        Dashboard(self.target.stats, self.overlay.progress).exec()

    def open_intro(self) -> None:
        if self.site_path is None or not self.site_path.is_file():
            QMessageBox.warning(None, 'ProfMonkey', '介绍页面未找到，请检查网站文件是否完整。')
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.site_path.resolve()))):
            QMessageBox.warning(None, 'ProfMonkey', '系统未能打开浏览器，请手动打开 site/index.html。')

    def _save(self) -> None:
        try:
            self.config.save(self.overlay.settings)
        except OSError as exc:
            QMessageBox.warning(None,'ProfMonkey 设置','无法保存设置：'+str(exc))

    def reset_position(self) -> None:
        self.colony.gather()

    def set_colony_behavior(self, behavior: str) -> None:
        self.colony.set_behavior(behavior)
        if behavior in self.behavior_actions:
            self.behavior_actions[behavior].setChecked(True)
        self._save()

    def set_collisions_enabled(self, enabled: bool) -> None:
        self.colony.set_collisions(enabled)
        self._save()

    def set_ambient_encounters(self, enabled: bool) -> None:
        self.colony.set_ambient_encounters(enabled)
        self._save()

    def set_civic_autonomy(self, enabled: bool) -> None:
        self.colony.set_civic_autonomy(enabled)
        self._save()

    def demo_encounter(self) -> None:
        if not self.colony.demo_encounter():
            QMessageBox.information(None, '🐒 猴山偶遇',
                '需要至少两只空闲的猴子；专注、暂停、短剧或投掷期间暂不能触发。')

    def choose_duo_pair(self) -> None:
        if self.colony.count < 2:
            QMessageBox.information(None, '🐒 猴山化学反应', '请先在猴山管理局增加至至少两只猴子。')
            return
        from core.profiles import PERSONALITIES
        labels = [f'#{i+1}  {pet.display_name} · {PERSONALITIES.get(pet.personality, "学究猴")}'
                  for i, pet in enumerate(self.colony.monkeys)]
        first, ok = QInputDialog.getItem(
            None, '🧪 猴山化学反应', '选择第一只猴子', labels, 0, False)
        if not ok:
            return
        first_index = labels.index(first)
        options = [(i, text) for i, text in enumerate(labels) if i != first_index]
        second, ok = QInputDialog.getItem(
            None, '🧪 猴山化学反应', '选择第二只猴子', [text for _, text in options], 0, False)
        if not ok:
            return
        second_index = next(i for i, text in options if text == second)
        if not self.colony.demo_pair(first_index, second_index):
            QMessageBox.information(None, '🐒 暂时无法演出',
                '两只猴子需可见且空闲；暂停、专注、拖动、联合短剧或香蕉竞速时暂不能触发。')

    def drop_shared_banana(self) -> None:
        if self.colony.drop_shared_banana():
            return
        if self.colony.count < 2:
            message = '公共香蕉竞速至少需要 2 只猴子。先在「猴子数量」里增加成员。'
        elif self.overlay.focus.active:
            message = '专注期间不举办香蕉竞速。结束专注后再试吧。'
        else:
            message = '猴子们现在忙着别的事情，或者香蕉竞速已经开始。请稍后再试。'
        QMessageBox.information(None, '🍌 公共香蕉', message)

    def random_story(self) -> None:
        import random
        self.start_story(random.choice(('banana','blackboard','mirror','keyboard','edge')))

    def set_mode(self, mode):
        self.colony.set_mode(mode)
        self._save()

    def stop_story(self):
        self.target.story.cancel()
        self.target._story_index = -1
        self.target._speech = ''
        self.target.body.vx = 0
        self.target.player.request('idle', force=True, restart=True)
        self.target._set_current_sprite(force=True)

    def play_once(self,name):
        if self.overlay.focus.active:
            self.target._say('专注中，结束后再表演～')
            return
        self.demo_action.setChecked(False)
        self.pause_action.setChecked(False)
        self.target.play_action(name)

    def start_story(self,name):
        if self.overlay.focus.active:
            self.target._say('教授正在陪你专注～')
            return
        self.demo_action.setChecked(False)
        self.pause_action.setChecked(False)
        if not self.target.start_story(name):
            self.target._say('先让当前事故结束～')
        else:
            self.quests.record('story')

    def restore(self) -> None:
        self.colony.show_all()

    def set_topmost(self, enabled: bool) -> None:
        self.colony.set_topmost(enabled)
        self._save()

    def select_target(self, overlay: MonkeyOverlay) -> None:
        """Right-clicking one monkey makes interactions target that monkey."""
        self.target = overlay

    def refresh_count_label(self) -> None:
        self.count_action.setText(f'🐒 猴子数量：{self.colony.count} 只 · 点击调整')

    def choose_count(self) -> None:
        dialog = MonkeyCountDialog(self.colony.count)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_count(dialog.selected())

    def update_count(self, count: int) -> None:
        """Immediate count change, persisted locally, no application restart."""
        self.colony.set_count(count)
        self.overlay.settings.monkey_count = self.colony.count
        if self.target not in self.colony.monkeys:
            self.target = self.overlay
        self.refresh_count_label()
        self.update_focus_ui()
        self._save()

    def open_colony_panel(self) -> None:
        dialog = ColonyPanel(self.overlay.settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.updated(self.overlay.settings)
        self.colony.configure(updated)
        self.refresh_count_label()
        self.update_focus_ui()
        if self.target not in self.colony.monkeys:
            self.target=self.overlay
        self._save()
        if dialog.action != 'save':
            self.launch_social(dialog.action)

    def launch_social(self, kind: str) -> None:
        if self.colony.start_social(kind):
            return
        QMessageBox.information(None,'猴山委员会',
            '至少需要 2 只猴子，且必须处于非暂停、非专注、非其他短剧状态。\n'
            '可用「猴山管理局」调整猴子数量。')


    def feed_target(self) -> None:
        if self.target.feed_banana():
            self.quests.record('feed')

    def show_quests(self) -> None:
        QuestDialog(self.quests, self.colony.count).exec()

    def set_chronicle_enabled(self, enabled: bool) -> None:
        self.colony.set_chronicle_enabled(enabled)
        if self.chronicle_action.isChecked() != enabled:
            self.chronicle_action.setChecked(enabled)
        self._save()

    def show_chronicle(self) -> None:
        ChronicleDialog(self.colony, self.chronicle, self.set_chronicle_enabled).exec()

    def open_council(self) -> None:
        if self.colony.count < 3:
            QMessageBox.information(None, '🗳 猴山议会',
                '至少需要三只猴子。请先在「猴子数量」或「猴山管理局」里增加成员。')
            return
        CouncilDialog(self.colony).exec()

    def show_laws(self) -> None:
        MonkeyLawDialog(self.colony, self.laws).exec()

    def show_expeditions(self) -> None:
        ExpeditionDialog(self.colony).exec()

    def show_civilization(self) -> None:
        CivilizationDialog(self.colony).exec()

    def show_city_life(self, case_id: str | None = None) -> None:
        CityLifeDialog(self.colony, case_id).exec()

    def show_evolution(self) -> None:
        EvolutionDialog(self.colony).exec()

    def show_society(self) -> None:
        SocietyDialog(self.colony, self._save).exec()
        # Both switches can change in the dedicated dialog. Synchronize tray
        # without retriggering the same callbacks or extra writes.
        for action, checked in (
            (self.civic_action, self.overlay.settings.civic_autonomy),
            (self.ambient_action, self.overlay.settings.ambient_encounters),
        ):
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)

    def show_character_lineup(self) -> None:
        from ui.character_gallery import CharacterGallery
        CharacterGallery(self.colony).exec()

    def open_relationships(self) -> None:
        RelationshipDialog(self.relationships, self.overlay.settings.monkey_profiles,
                           self.colony.count).exec()

    def place_furniture(self, kind: str) -> None:
        if not self.colony.place_furniture(kind):
            QMessageBox.information(None, '猴山家具', '最多同时摆放 8 件家具，或者道具类型无效。先收起几件再试。')

    def export_story_card(self) -> None:
        names = list(STORIES)
        labels = [f'{key} · {STORIES[key][0]}' for key in names]
        choice, ok = QInputDialog.getItem(None, '导出猴山故事卡', '选择一个故事主题', labels, 0, False)
        if not ok or not choice:
            return
        key = names[labels.index(choice)]
        filename, _ = QFileDialog.getSaveFileName(None, '保存猴山故事卡',
                    f'ProfMonkey_故事卡_{key}.png', 'PNG 图片 (*.png)')
        if not filename:
            return
        relation_line = ''
        if self.colony.count >= 2:
            rel = self.relationships.get(0, 1)
            relation_line = f'{self.overlay.settings.monkey_profiles[0]["name"]} 与 {self.overlay.settings.monkey_profiles[1]["name"]}：{rel["label"]}'
        try:
            size = render_story_card(self.colony.image, self.overlay.settings.monkey_profiles,
                                     self.colony.count, key, Path(filename), relation_line)
            QMessageBox.information(None, '故事卡已保存',
                f'已导出 {size[0]}×{size[1]} PNG。只使用猴子素材和故事文案，不包含桌面截图。')
        except (OSError, ValueError, ImportError) as exc:
            QMessageBox.warning(None, '导出失败', str(exc))

    def export_portrait(self) -> None:
        filename,_=QFileDialog.getSaveFileName(None,'保存猴山合照',
                    'ProfMonkey_猴山合照.png','PNG 图片 (*.png)')
        if not filename:
            return
        try:
            from core.portrait import render_colony_portrait
            image = self.colony.image
            size = render_colony_portrait(image,self.overlay.settings.monkey_profiles,
                                          self.colony.count,Path(filename))
            QMessageBox.information(None,'猴山合照已保存',
                 f'导出 {size[0]}×{size[1]} PNG 完成。只合成原创猴子素材，不截图。')
        except (OSError,ValueError,ImportError) as exc:
            QMessageBox.warning(None,'合照失败',str(exc))

    def edit_settings(self) -> None:
        dlg = SettingsDialog(self.overlay.settings)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new = dlg.value(self.overlay.settings)
            self.colony.configure(new)
            if self.target not in self.colony.monkeys:
                self.target = self.overlay
            self.refresh_count_label()
            self.mode_actions[new.mode].setChecked(True)
            self.ambient_action.setChecked(new.ambient_encounters)
            self.chronicle_action.setChecked(new.chronicle_enabled)
            if self.topmost_action.isChecked()!=new.always_on_top:
                self.topmost_action.setChecked(new.always_on_top)
            self._save()

    def export_gif(self) -> None:
        if not self.manifest:
            return
        names = sorted(self.overlay.player.specs)
        name,ok = QInputDialog.getItem(None,'导出原创动作 GIF','选择动作',names,0,False)
        if not ok or not name:
            return
        filename,_ = QFileDialog.getSaveFileName(None,'保存 GIF',f'ProfMonkey_{name}.gif','GIF 文件 (*.gif)')
        if filename:
            try:
                from core.export import export_action_gif
                count = export_action_gif(self.manifest,name,Path(filename),
                                          personality=self.target.personality)
                QMessageBox.information(None,'导出成功',f'已导出 {count} 帧角色动画；不会包含桌面内容。')
            except (OSError,ValueError,ImportError) as exc:
                QMessageBox.warning(None,'导出失败',f'{exc}\n需要安装 Pillow: pip install Pillow')

    def export_story(self) -> None:
        if not self.manifest:
            return
        from core.events import SCRIPTS
        names = [n for n in SCRIPTS if n != 'banana_safe']
        name, ok = QInputDialog.getItem(None, '导出完整短剧', '选择故事', names, 0, False)
        if not ok or not name:
            return
        filename, _ = QFileDialog.getSaveFileName(None, '保存故事 GIF', f'ProfMonkey_story_{name}.gif', 'GIF 文件 (*.gif)')
        if filename:
            try:
                from core.export import export_story_gif
                count = export_story_gif(self.manifest, name, Path(filename),
                                         personality=self.target.personality)
                QMessageBox.information(None, '导出成功', f'已导出 {count} 帧原创剧情卡片，无任何桌面截图。')
            except (OSError, ValueError, ImportError) as exc:
                QMessageBox.warning(None, '导出失败', str(exc))

    def show_history(self) -> None:
        h = self.overlay.history
        if h is None or not h.enabled:
            QMessageBox.information(None,'事件档案','本地事件收藏默认关闭；可在设置中开启。')
        else:
            lines = [f"{e.get('at','')} · {e.get('event','')}" for e in h.entries[-25:]]
            QMessageBox.information(None,'事件档案','\n'.join(lines) if lines else '还没有完成的事件。')

    def clear_history(self) -> None:
        if self.overlay.history:
            self.overlay.history.clear()
        QMessageBox.information(None,'事件档案','本地事件收藏已清空。')

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        self.target = self.overlay
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.colony.visible():
                self.colony.hide_all()
            else:
                self.restore()

    def quit(self) -> None:
        self._focus_timer.stop()
        self.tray.hide()
        self.colony.quit_all()
        self.app.quit()
