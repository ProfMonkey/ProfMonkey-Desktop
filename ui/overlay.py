"""ProfMonkey v0.9 desktop overlay (colony life candidate build).

No global keyboard hooks, clipboard APIs, screenshot APIs, window manipulation,
or real cursor movement. Shaped top-level window means empty pixels should pass
through on Windows; MUST still be verified on a physical Windows desktop.
"""
from __future__ import annotations
import math
import random
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QGuiApplication, QImage, QPainter, QPen, QPixmap, QRegion, QTransform
from PySide6.QtWidgets import QMenu, QWidget

from core.animation import AnimationPlayer, DemoTimeline, load_manifest
from core.alpha_mask import opaque_spans
from core.config import Settings
from core.focus import FocusClock
from core.progress import ProgressStore
from core.events import StoryDirector
from core.history import History
from core.physics import Body
from core.profiles import clean_profiles
from core.state import Brain, PetState
from ui.character_render import render_mascot
from ui.audio import SoundBank

ALPHA_HIT_THRESHOLD = 24


def sprite_window_mask(sprite: QPixmap) -> QRegion:
    """Convert transparent sprite pixels into an actual window hit region."""
    image = sprite.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    rows = ([image.pixelColor(x, y).alpha() for x in range(image.width())] for y in range(image.height()))
    region = QRegion()
    for y, x0, x1 in opaque_spans(rows, threshold=ALPHA_HIT_THRESHOLD):
        region = region.united(QRegion(QRect(x0, y, x1-x0, 1)))
    return region


class MonkeyOverlay(QWidget):
    def __init__(self, image_file: Path, manifest_file: Path | None = None,
                 *, settings: Settings | None = None, history: History | None = None,
                 progress: ProgressStore | None = None,
                 focus: FocusClock | None = None, is_primary: bool = True,
                 seed: int = 20261025, monkey_index: int = 0) -> None:
        super().__init__(None)
        self.settings = (settings or Settings()).validated()
        self.history = history
        self.progress = progress
        self.focus = focus if focus is not None else FocusClock()
        self.is_primary = is_primary
        # Set by MonkeyColony after local SecretJournal is attached. Never
        # reaches keyboard hooks or real user documents.
        self.secret_gesture = None
        self.monkey_index = monkey_index
        self.display_name = ''
        self.personality = 'scholar'
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowDoesNotAcceptFocus |
                            Qt.WindowType.NoDropShadowWindowHint |
                            (Qt.WindowType.WindowStaysOnTopHint if self.settings.always_on_top else Qt.WindowType.Widget))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle('ProfMonkey Desktop · v0.20 六猴原创形象候选')
        self.setToolTip('ProfMonkey 🐒 左键轻戳或拖动；右键菜单')
        self.setMouseTracking(True)
        self._menu: QMenu | None = None
        self._before_context_menu = None
        self._art_root = (manifest_file or image_file.parent/'manifest.json').parent
        # v0.20: all 6 mascots are vector originals. Do not load obsolete,
        # missing v0.9 idle.png or reuse one giant-headed image for everyone.
        first_profile = clean_profiles(self.settings.monkey_profiles)[monkey_index]
        self._fallback = render_mascot(self._art_root, first_profile['personality'])
        if self._fallback.isNull():
            raise ValueError('six-monkey artwork missing or invalid')
        self.player = AnimationPlayer(load_manifest(manifest_file or image_file.parent/'manifest.json'))
        self.stats = PetState(mode=self.settings.mode)
        self.brain = Brain(seed=seed)
        self.configure_profile(clean_profiles(self.settings.monkey_profiles)[monkey_index])
        self.story = StoryDirector(on_finish=self._story_finished)
        self.audio = SoundBank(self._art_root.parent/"audio", self)
        self.audio.set_enabled(self.settings.sound)
        self._rng = random.Random(seed)
        self.body = Body()
        self._on_ground = True
        self._fallback_original = self._fallback
        self._sprite_cache: dict[tuple[str,int,int,int],QPixmap] = {}
        self._missing_frames: set[str] = set()
        self._hit_cache: dict[tuple[str,int,int,int],QRegion] = {}
        self._display_key = None
        self._sprite = self._fallback
        self._hit_region = QRegion()
        self._drag_active = False
        self._press_global: QPoint | None = None
        self._press_window: QPoint | None = None
        self._drag_samples: deque[tuple[float,QPoint]] = deque(maxlen=8)
        self._drag_moved = False
        self._drag_started = 0.0
        self._click_times: deque[float] = deque(maxlen=6)
        self._paused = False
        self._social_active = False
        self._demo_enabled = False
        self._colony_target_x: float | None = None
        self._colony_target_speed = 95.0
        self._collision_reaction_until = 0.0
        self.demo = DemoTimeline()
        self._turn_flipped = False
        self._speech = ''
        self._speech_until = 0.0
        self._story_index = -1
        # First-run onboarding: a demonstration within the first minute.
        # Later quiet-mode stories follow the longer user-configurable cooldown.
        self._next_story_at = time.monotonic() + 40
        self._last_tick = time.monotonic()
        self._last_facing = 0.0
        self._last_move = None
        self._resize_canvas(self.settings.size)
        self._set_current_sprite(force=True)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @property
    def demo_enabled(self) -> bool:
        return self._demo_enabled

    @property
    def paused(self) -> bool:
        return self._paused

    def _resize_canvas(self, sprite_size: int) -> None:
        self._size = sprite_size
        self.setFixedSize(max(278, sprite_size+112), sprite_size+76)
        self._sx = (self.width()-sprite_size)//2 - 9
        self._sy = self.height()-sprite_size-5
        self._sprite_cache.clear()
        self._hit_cache.clear()
        self._display_key = None

    def _interval(self) -> float:
        base = self.settings.monkey_interval if self.settings.mode == 'MONKEY' else self.settings.quiet_interval
        return base * self._rng.uniform(.8, 1.2)

    def configure(self, updated: Settings) -> None:
        oldsize = self.settings.size
        self.settings = updated.validated()
        self.stats.mode = self.settings.mode
        self.configure_profile(self.settings.monkey_profiles[self.monkey_index])
        self.audio.set_enabled(self.settings.sound)
        if oldsize != self.settings.size:
            self._resize_canvas(self.settings.size)
            self._set_current_sprite(force=True)
            self._ensure_onscreen()
        self._next_story_at = time.monotonic() + self._interval()
        if self.history:
            self.history.enabled = self.settings.history
        if self.progress:
            if self.settings.progress_enabled:
                self.progress.enable()
            else:
                self.progress.disable()
        self.update()

    def configure_profile(self, profile: dict) -> None:
        from core.profiles import clean_name, PERSONALITIES
        self.display_name = clean_name(profile.get('name'), self.monkey_index)
        personality = profile.get('personality', 'scholar')
        previous = self.personality
        self.personality = personality if personality in PERSONALITIES else 'scholar'
        self.brain.personality = self.personality
        self.setToolTip(f'{self.display_name} · {PERSONALITIES[self.personality]} · 左键拖动；右键菜单')
        # A user changing their personality immediately changes their actual
        # full-body sprite, hit region and all future animations. No stale
        # professor frame remains in a companion's cache.
        if previous != self.personality and hasattr(self, '_sprite_cache'):
            self._fallback = render_mascot(self._art_root, self.personality)
            self._fallback_original = self._fallback
            self._sprite_cache.clear()
            self._hit_cache.clear()
            self._display_key = None
            self._set_current_sprite(force=True)

    def set_colony_target(self, target_x: float | None, speed: float = 95.0) -> None:
        self._colony_target_x = None if target_x is None else float(target_x)
        self._colony_target_speed = max(35.0, min(190.0, float(speed)))

    def react_to_colony_collision(self, other_name: str, push_direction: int) -> None:
        """Show a short reaction to contact with another independent pet."""
        now = time.monotonic()
        if now < self._collision_reaction_until or self._paused or self.focus.active:
            return
        self._collision_reaction_until = now + 1.35
        self.stats.mood = max(-100.0, self.stats.mood - 3.0)
        self.brain.remaining = max(self.brain.remaining, 1.1)
        self.player.face(1 if push_direction >= 0 else -1)
        action = 'blink' if self.personality == 'sleepy' else 'angry'
        self.stats.action = action
        self.player.request(action, force=True, restart=True)
        self._say(f'撞到{other_name}了！', 1.5)
        self._set_current_sprite(force=True)

    def social_pose(self, action: str, line: str) -> None:
        """Stage a skit using *this* pet's animation and local speech bubble."""
        self.play_action(action)
        self._social_active = True
        self.body.vx = self.body.vy = 0.0
        self.body.airborne = False
        self._say(f'{self.display_name}：{line}', 4.2)

    def exit_social(self) -> None:
        if self._social_active:
            self._social_active = False
            self.body.vx = 0.0
            self.stats.action = 'idle'
            self.brain.remaining = 1.5
            self.player.request('idle', force=True, restart=True)
            self._set_current_sprite(force=True)

    def set_mode(self, mode: str) -> None:
        self.settings.mode = mode if mode in ('QUIET','MONKEY') else 'QUIET'
        self.stats.mode = self.settings.mode
        self._next_story_at = time.monotonic() + self._interval()
        self._say('猴山开会！' if mode == 'MONKEY' else '安静学习中', 1.8)

    def _say(self, message: str, duration: float = 2.3) -> None:
        self._speech = message
        self._speech_until = time.monotonic()+duration
        self._update_mask()
        self.update()

    def _record_progress(self, kind: str, amount: int = 1) -> None:
        if self.progress is None:
            return
        try:
            awards = self.progress.record(kind, amount)
        except OSError:
            # A read-only profile must not break the pet.
            return
        if awards:
            self._say('解锁：' + awards[0], 3.2)

    def start_focus(self, minutes: int) -> None:
        self.set_colony_target(None)
        self.focus.start(minutes)
        self.story.cancel()
        self._demo_enabled = False
        self._story_index = -1
        self.body.vx = 0
        self.stats.action = 'idle'
        self.player.request('idle', force=True, restart=True)
        self._set_current_sprite(force=True)
        self._say(f'专注 {minutes} 分钟，猴子陪你！', 3.0)

    def _focus_completed(self) -> None:
        self._record_progress('focus_sessions')
        self._record_progress('focus_minutes', self.focus.minutes)
        self.stats.mood = min(100., self.stats.mood + 16)
        self._say('专注完成！教授批准休息 🍌', 4.0)
        self.audio.play('win')
        self.play_action('wake')
        # play_action clears temporary messages, so display the success last.
        self._say('专注完成！教授批准休息 🍌', 4.0)

    def feed_banana(self) -> bool:
        if self.focus.active:
            self._say('先完成专注，再来吃香蕉～')
            return False
        self.story.cancel()
        self._story_index = -1
        self.stats.energy = min(100., self.stats.energy + 12)
        self.stats.mood = min(100., self.stats.mood + 9)
        self.play_action('eat_banana')
        self.audio.play('banana')
        self._say('香蕉到账！猴力恢复 🍌')
        self._record_progress('feeds')
        if self.secret_gesture is not None:
            self.secret_gesture('feed', self)
        return True

    def say_quote(self) -> str:
        lines = self.settings.custom_quotes or [
            '宇宙很大，猴子很忙。', '文明，就是猴子学会穿西装。',
            '1+1=猴，这是严谨的。', '今日无事，研究香蕉。',
            '教授声明：摔倒是实验的一部分。',
        ]
        phrase = self._rng.choice(lines)
        self._say(phrase, 3.8)
        return phrase

    def _sprite_for(self, key):
        if key in self._sprite_cache:
            return self._sprite_cache[key]
        name, idx, facing, size = key
        # Action timings/frames remain in the v0.9 manifest, but the actual
        # drawing is regenerated per persona. Missing old PNGs are irrelevant.
        spec = self.player.specs[name]
        try:
            pix = render_mascot(self._art_root, self.personality,
                                name, idx, len(spec.frames))
        except (OSError, ValueError):
            self._missing_frames.add(f'{self.personality}:{name}:{idx}')
            pix = self._fallback_original
        pix = pix.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if facing == -1:
            pix = pix.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
        self._sprite_cache[key] = pix
        return pix

    def _set_current_sprite(self, force=False) -> None:
        key = (self.player.action, self.player.frame_index, self.player.facing, self._size)
        if not force and key == self._display_key:
            return
        self._display_key = key
        self._sprite = self._sprite_for(key)
        region = self._hit_cache.get(key)
        if region is None:
            region = sprite_window_mask(self._sprite)
            if region.isEmpty():
                region = sprite_window_mask(self._fallback_original.scaled(self._size,self._size))
            self._hit_cache[key] = region
        self._hit_region = region.translated(self._sx, self._sy)
        self._update_mask()
        self.update()

    def _update_mask(self):
        if self._drag_active:
            return
        area = self._hit_region
        if self.story.active or (self._speech and time.monotonic() < self._speech_until):
            area = area.united(QRegion(QRect(10, 5, self.width()-20, 53)))
        if self.story.active and self.story.beat and self.story.beat.prop:
            area = area.united(QRegion(QRect(self.width()-67, self.height()-64 if self.story.beat.prop == 'peel' else 73, 65, 70)))
            if self.story.beat.prop == 'mirror_twins':
                area = area.united(QRegion(QRect(2,self.height()-103,94,95)))
                area = area.united(QRegion(QRect(self.width()-90,self.height()-103,88,95)))
        self.setMask(area)

    def _work_area(self):
        screen = QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()
        if screen is None:
            return (0., 0., 1280., 720.)
        rect = screen.availableGeometry()
        return (float(rect.x()), float(rect.y()), float(rect.right()+1), float(rect.bottom()+1))

    def position_bottom_right(self) -> None:
        left, top, right, bottom = self._work_area()
        self.body.x, self.body.y = right-self.width()-12, bottom-self.height()
        self.body.ground((left,top,right,bottom), (self.width(),self.height()))
        self.move(round(self.body.x), round(self.body.y))

    def _ensure_onscreen(self) -> None:
        bounds = self._work_area()
        if not self.body.airborne:
            self.body.ground(bounds, (self.width(),self.height()))
        else:
            self.body.x = max(bounds[0], min(bounds[2]-self.width(),self.body.x))
        self.move(round(self.body.x), round(self.body.y))

    def _story_finished(self, name: str) -> None:
        if self.history:
            self.history.add(name)
        self._speech = ''
        self._story_index = -1
        self.stats.action = 'idle'
        self.player.request('idle', force=True, restart=True)
        self.body.vx = 0
        self._next_story_at = time.monotonic() + self._interval()
        self._update_mask()
        self._record_progress('stories')

    def start_story(self, name: str, *, safe: bool | None = None) -> bool:
        if self._drag_active or self.focus.active or self._social_active:
            return False
        self._demo_enabled = False
        self.set_colony_target(None)
        if self.story.start(name, safe=safe):
            self.brain.remaining = 2.0
            self.body.vx = 0
            self._story_index = -1
            self._apply_story_beat()
            return True
        return False

    def _apply_story_beat(self) -> None:
        beat = self.story.beat
        if beat is None:
            self._update_mask()
            return
        if self._story_index == self.story.index:
            return
        self._story_index = self.story.index
        action = beat.action
        self.stats.action = action
        self.player.request(action, force=True, restart=True)
        self.body.vx = (65 if self.player.action in ('walk','run') else 0) * self.player.facing
        self._speech = beat.line
        sound = {'eat_banana':'banana','slip':'slip','fall':'fall','get_up':'win'} .get(action)
        if sound:
            self.audio.play(sound)
        self._speech_until = float('inf')
        self._set_current_sprite(force=True)
        self._update_mask()

    def play_action(self, name: str) -> None:
        if self.focus.active:
            return
        self.set_colony_target(None)
        self._social_active = False  # explicit local action cancels group control
        self._demo_enabled = False
        self.story.cancel()
        self._story_index = -1
        self.body.vx = 0.0
        self._speech = ''
        self.stats.action = name
        self.player.request(name, force=True, restart=True)
        self._set_current_sprite(force=True)

    def toggle_demo(self, enabled: bool) -> None:
        if enabled and self.focus.active:
            return
        self.set_colony_target(None)
        self._demo_enabled = enabled
        self.story.cancel()
        self.body.vx = 0
        self._speech = ''
        self.demo.reset()
        self.player.request('idle',force=True,restart=True)
        self._set_current_sprite(force=True)

    def toggle_pause(self, enabled: bool) -> None:
        self._paused = enabled
        self.player.paused = enabled
        self._last_tick = time.monotonic()
        self._update_mask()

    def _decide_movement(self, chosen):
        if chosen == 'run':
            # Chase/avoid is visual movement only, never moves the system cursor.
            if self.settings.mode == 'MONKEY':
                cursor_x = QCursor.pos().x()
                me_x = self.body.x + self.width()/2
                if abs(cursor_x - me_x) < 370:
                    toward = 1 if cursor_x >= me_x else -1
                    self.player.face(-toward if self.stats.mood < -20 else toward)
            self.body.vx = 135*self.player.facing
        elif chosen == 'walk':
            self.body.vx = 55*self.player.facing
        else:
            self.body.vx = 0
        self.stats.action = chosen
        self.player.request(chosen,force=True,restart=True)
        self._set_current_sprite()

    def _tick(self) -> None:
        now = time.monotonic()
        dt = max(0., min(.12, now-self._last_tick))
        self._last_tick = now
        if self.is_primary and self.focus.check_complete(now):
            self._focus_completed()
        if self._drag_active:
            # Recovery if an OS task switch swallows the mouse-release event.
            # 15s timeout is a fail-safe, not normal drag duration behavior.
            if (not (QGuiApplication.mouseButtons() & Qt.MouseButton.LeftButton)
                    or now - self._drag_started > 15.0):
                self._clear_drag()
                self.body.ground(self._work_area(),(self.width(),self.height()))
                self.move(round(self.body.x),round(self.body.y))
            return
        if self._paused or not self.isVisible():
            return
        self.player.advance(dt)
        if self.body.airborne:
            self.body.step(dt, self._work_area(), (self.width(),self.height()))
            if not self.body.airborne:
                self._decide_movement('idle')
        elif self.story.active:
            if self.story.advance(dt):
                self._story_index = -1
                self._apply_story_beat()
            if self.story.active and self.body.vx:
                self.body.step(dt,self._work_area(),(self.width(),self.height()))
        elif self.focus.active:
            # Focus always supersedes autonomous movement and surprise stories.
            if self.stats.action != 'idle' or self.body.vx:
                self.body.vx = 0
                self.stats.action = 'idle'
                self.player.request('idle', force=True, restart=True)
        elif self._social_active:
            # Social director owns temporary poses; brain must not overwrite.
            self.body.vx = 0.0
        elif self._demo_enabled:
            new_action = self.demo.advance(dt)
            if new_action:
                self.player.request(new_action, force=True, restart=True)
                self.body.vx = 0
        elif self._colony_target_x is not None:
            delta_x = self._colony_target_x - self.body.x
            if abs(delta_x) <= 22.0:
                self.body.vx = 0.0
                if self.player.action != 'idle':
                    self.stats.action = 'idle'
                    self.player.request('idle', force=True, restart=True)
                    self._set_current_sprite(force=True)
            else:
                direction = 1 if delta_x > 0 else -1
                changed_facing = self.player.facing != direction
                self.player.face(direction)
                desired_action = 'run' if self._colony_target_speed >= 125 else 'walk'
                if self.player.action != desired_action or changed_facing:
                    self.stats.action = desired_action
                    self.player.request(desired_action, force=True, restart=True)
                    self._set_current_sprite(force=True)
                self.body.vx = self._colony_target_speed * direction
                self.body.step(dt, self._work_area(), (self.width(), self.height()))
        else:
            self.stats.tick(dt)
            choice = self.brain.next(self.stats,dt)
            if choice:
                self._decide_movement(choice)
            if self.body.vx:
                self.body.step(dt,self._work_area(),(self.width(),self.height()))
            # No consented global activity tracking: autonomous stories only.
            if self.is_primary and self.settings.stories and now > self._next_story_at:
                self.start_story(self._rng.choice(('banana','blackboard','mirror','edge')))
                self._next_story_at = now + self._interval()
            if self.player.action in ('idle','blink') and now-self._last_facing > 2.0:
                center = self.x()+self._sx+self._size//2
                self.player.face(1 if QCursor.pos().x() >= center else -1)
                self._last_facing = now
        if self.body.vx and not self.body.airborne:
            left, _top, right, _bottom = self._work_area()
            if (self.body.x <= left+1 and self.body.vx < 0) or (self.body.x >= right-self.width()-1 and self.body.vx > 0):
                self.player.face(-self.player.facing)
                self.body.vx = abs(self.body.vx)*self.player.facing
        xy = (round(self.body.x), round(self.body.y))
        if xy != self._last_move:
            self.move(*xy)
            self._last_move = xy
        if self._speech and not self.story.active and now >= self._speech_until:
            self._speech = ''
            self._update_mask()
            self.update()
        self._set_current_sprite()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_colony_target(None)
            self.exit_social()  # an ordinary user drag interrupts the skit
            self._press_global = event.globalPosition().toPoint()
            self._press_window = self.pos()
            self._drag_samples.clear()
            self._drag_samples.append((time.monotonic(),self._press_global))
            self._drag_active, self._drag_moved = True, False
            self._drag_started = time.monotonic()
            self.body.vx = self.body.vy = 0
            self.body.airborne = False
            self.setMask(QRegion(self.rect()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active and self._press_global is not None and self._press_window is not None:
            pos = event.globalPosition().toPoint()
            delta = pos-self._press_global
            if (abs(delta.x())+abs(delta.y()))>8:
                self._drag_moved = True
            if self._drag_moved:
                self.body.x = self._press_window.x()+delta.x()
                self.body.y = self._press_window.y()+delta.y()
                self._ensure_drag_bounds()
                self.move(round(self.body.x),round(self.body.y))
                self._drag_samples.append((time.monotonic(),pos))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _ensure_drag_bounds(self) -> None:
        l,t,r,b = self._work_area()
        self.body.x = min(max(l,self.body.x),max(l,r-self.width()))
        self.body.y = min(max(t,self.body.y),max(t,b-self.height()))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            if self._drag_moved:
                last = event.globalPosition().toPoint()
                now = time.monotonic()
                self._drag_samples.append((now,last))
                earlier = next(((t,p) for t,p in self._drag_samples if now-t <= .17), self._drag_samples[0])
                elapsed = max(.04, now-earlier[0])
                self.body.throw((last.x()-earlier[1].x())/elapsed*.55,
                                (last.y()-earlier[1].y())/elapsed*.55)
                self.player.request('dragged',force=True,restart=True)
                self.brain.remaining = 2.0
                self._record_progress('throws')
            else:
                if not (self.story.rescue_peel() or self.story.correct_blackboard()):
                    self.stats.tap()
                    self._record_progress('taps')
                    self.audio.play('click')
                    now = time.monotonic()
                    self._click_times.append(now)
                    tapped = sum(1 for t in self._click_times if now-t<4.)
                    self._say('别戳了！' if tapped>=4 else self._rng.choice(('嗯？','教授在思考','你点我干嘛？')))
                    if tapped == 4 and self.secret_gesture is not None:
                        self.secret_gesture('rapid_tap', self)
                    self.player.request('angry' if tapped>=4 else 'blink',force=True,restart=True)
                else:
                    self._story_index = -1
                    self._apply_story_beat()
            self._clear_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _clear_drag(self) -> None:
        self._drag_active = False
        self._press_global = self._press_window = None
        self._drag_samples.clear()
        self._update_mask()

    def hideEvent(self,event) -> None:
        self._clear_drag()
        self.body.vx = 0
        super().hideEvent(event)

    def reapply_hit_region(self) -> None:
        self._update_mask()

    def set_context_menu(self, menu: QMenu, on_open=None) -> None:
        self._menu = menu
        self._before_context_menu = on_open

    def contextMenuEvent(self,event) -> None:
        if self._menu is not None:
            if self._before_context_menu is not None:
                self._before_context_menu(self)
            self._menu.exec(event.globalPos())
            event.accept()
        else:
            super().contextMenuEvent(event)

    def paintEvent(self,event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # Animated in-app character only; never any real desktop pixels.
        p.drawPixmap(self._sx,self._sy,self._sprite)
        # Modest decorative costume accents for three palette variants.
        if self.settings.skin != 'professor':
            accent = {'night':'#7257CD','suit':'#172E47','exam':'#4BA57B'}[self.settings.skin]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(accent))
            cx = self._sx + self._size*.5
            yy = self._sy + self._size*.83
            p.drawRoundedRect(QRectF(cx-7,yy-3,14,16),3,3)
        beat = self.story.beat
        if beat and beat.prop:
            self._paint_prop(p, beat.prop)
            if beat.prop == 'mirror_twins':
                twin = self._sprite.scaled(95,95,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
                p.setOpacity(.82)
                p.drawPixmap(3,self.height()-103,twin)
                p.setOpacity(.65)
                p.drawPixmap(self.width()-94,self.height()-102,twin)
                p.setOpacity(1.0)
        if self.story.active or (self._speech and time.monotonic()<self._speech_until):
            text = beat.line if beat else self._speech
            p.setPen(QPen(QColor('#564433'), 1.5))
            p.setBrush(QBrush(QColor('#FFF1C9')))
            p.drawRoundedRect(QRectF(10,5,self.width()-20,53),14,14)
            f = QFont('Microsoft YaHei',11)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor('#4A302B'))
            p.drawText(QRectF(16,7,self.width()-32,49),Qt.AlignmentFlag.AlignCenter,text)
        p.end()

    def _paint_prop(self,p:QPainter,kind:str) -> None:
        x, y = self.width()-65, self.height()-56 if kind=='peel' else 77
        p.save()
        p.setPen(QPen(QColor('#4A302B'), 2))
        if kind in ('banana','peel'):
            p.setBrush(QColor('#F9D74B'))
            p.drawArc(QRectF(x+2,y,44,38),-65*16,190*16)
            if kind == 'peel':
                p.drawLine(x+17,y+20,x+1,y+42)
                p.drawLine(x+17,y+20,x+38,y+49)
        elif kind in ('board','keyboard','keyboard_broken'):
            p.setBrush(QColor('#316253') if kind == 'board' else QColor('#9EC4CD'))
            p.drawRoundedRect(QRectF(x,y,61,43),4,4)
            if kind == 'board':
                p.setPen(QColor('white'))
                p.setFont(QFont('Arial',8))
                p.drawText(QRectF(x+2,y+2,57,38),Qt.AlignmentFlag.AlignCenter,
                           '1+1=猴' if self.story.index>=3 else '1+1=3')
            else:
                p.setPen(QPen(QColor('#607981'),2))
                for i in range(4):
                    p.drawLine(x+7,y+10+i*7,x+53,y+10+i*7)
        elif kind.startswith('mirror'):
            p.setBrush(QColor('#B9E3F2'))
            p.drawEllipse(QRectF(x,y,51,51))
            p.setBrush(QColor('#8A5A3B'))
            p.drawEllipse(QRectF(x+14,y+14,23,23))
            if kind=='mirror_twins':
                p.drawEllipse(QRectF(x-11,y+18,15,15))
        elif kind=='sign':
            p.setBrush(QColor('#F8DFC1'))
            p.drawRoundedRect(QRectF(x,y,58,43),3,3)
            p.setPen(QColor('#8C362C'))
            p.setFont(QFont('Microsoft YaHei',10,QFont.Weight.Bold))
            p.drawText(QRectF(x+1,y+1,56,41),Qt.AlignmentFlag.AlignCenter,'甩锅')
        p.restore()
