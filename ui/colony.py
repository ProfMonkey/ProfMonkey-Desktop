"""Manage real, separate desktop monkey windows with one shared control menu.

Every monkey has its own brain, animation, body, stories and mouse events.
Only the primary monkey owns the focus-completion notification and schedules
background surprise stories, preventing 6 simultaneous interruptions.
"""
from __future__ import annotations
from pathlib import Path
import random
import time
from PySide6.QtCore import QTimer
from typing import Callable

from core.colony import clamp_count, spawn_position
from core.colony_physics import clamp_x, resolve_horizontal_collision
from core.social import GroupStory
from core.profiles import clean_profiles
from core.relationships import RelationshipStore
from core.quests import QuestBoard
from core.encounters import EncounterDirector, Participant, Encounter
from core.duo_story import DuoStory
from core.council import CouncilStory, Seat, prepare_council
from core.governance import MonkeyLaws
from core.expeditions import ExpeditionStory, ExpeditionJournal, Explorer, plan_expedition, LAW_BONUS
from core.civilization import BUILDINGS
from core.city_life import (CityLifeStory, CASE_TITLES, prepare_city_case)
from core.chronicle import ChronicleStore, Chapter
from ui.furniture import FurnitureWidget, PROPS
from core.config import Settings
from ui.overlay import MonkeyOverlay
from ui.banana_token import BananaTokenOverlay


class MonkeyColony:
    def __init__(self, primary: MonkeyOverlay, image: Path, manifest: Path) -> None:
        self.primary = primary
        self.image = image
        self.manifest = manifest
        self.monkeys: list[MonkeyOverlay] = [primary]
        self._menu = None
        self._on_menu_open: Callable[[MonkeyOverlay], None] | None = None
        self.social = GroupStory()
        self._social_timer = QTimer(primary)
        self._social_timer.setInterval(80)
        self._social_timer.timeout.connect(self._social_tick)
        self._last_social_tick = time.monotonic()
        self._next_social_at = self._last_social_tick + 300
        self._rng = random.Random(20261025)
        self._collision_cooldowns: dict[tuple[int, int], float] = {}
        self._relationship_cooldowns: dict[tuple[int, int], float] = {}
        self._banana_token: BananaTokenOverlay | None = None
        self._race_active = False
        self.relationships: RelationshipStore | None = None
        self.quests: QuestBoard | None = None
        self.chronicle: ChronicleStore | None = None
        self.laws: MonkeyLaws | None = None
        self.expeditions: ExpeditionJournal | None = None
        self._active_chapter: Chapter | None = None
        self.encounters = EncounterDirector()
        self.duo = DuoStory()
        self.council = CouncilStory()
        self.expedition = ExpeditionStory()
        self.city_life = CityLifeStory()
        self._on_city_event_open: Callable[[str], None] | None = None
        self.furniture: list[FurnitureWidget] = []
        self._social_timer.start()

    @property
    def count(self) -> int:
        return len(self.monkeys)

    def bind_city_story(self, open_case: Callable[[str], None]) -> None:
        """Let a finished desktop building open its specific in-game case."""
        self._on_city_event_open = open_case

    def bind_menu(self, menu, on_menu_open: Callable[[MonkeyOverlay], None]) -> None:
        self._menu = menu
        self._on_menu_open = on_menu_open
        for monkey in self.monkeys:
            monkey.set_context_menu(menu, on_menu_open)

    def set_count(self, count: int) -> None:
        """Grow/shrink immediately; preserve each remaining pet's position.

        This method does NOT save settings; the caller commits the accepted
        value to Settings/ConfigStore. Closing companions stops their timers.
        """
        target = clamp_count(count)
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_council()
        self.cancel_duo()
        if self.social.active:
            self.cancel_social()
        self.cancel_shared_banana()
        while self.count > target:
            pet = self.monkeys.pop()
            pet.story.cancel()
            pet._timer.stop()
            pet.audio.set_enabled(False)
            pet.hide()
            pet.close()
            pet.deleteLater()
        while self.count < target:
            idx = self.count
            pet = MonkeyOverlay(self.image, self.manifest,
                                settings=self.primary.settings,
                                history=self.primary.history,
                                progress=self.primary.progress,
                                focus=self.primary.focus,
                                is_primary=False,
                                seed=20261025 + idx * 1009,monkey_index=idx)
            if self._menu:
                pet.set_context_menu(self._menu, self._on_menu_open)
            pet.toggle_pause(self.primary.paused)
            point = spawn_position(self.primary._work_area(),
                                   (pet.width(), pet.height()), idx, target)
            pet.body.x, pet.body.y = map(float, point)
            pet.move(*point)
            self.monkeys.append(pet)
            if self.primary.isVisible():
                pet.show()
                pet.reapply_hit_region()
        self._collision_cooldowns.clear()
        self._relationship_cooldowns.clear()
        self.encounters.clear()
        self.apply_profiles()

    def apply_profiles(self) -> None:
        if self.city_life.active:
            self.cancel_city_life()
        if self.expedition.active:
            self.cancel_expedition()
        profiles = clean_profiles(self.primary.settings.monkey_profiles)
        for idx, pet in enumerate(self.monkeys):
            pet.configure_profile(profiles[idx])

    def configure(self, settings: Settings) -> None:
        """Apply a global preference to every independent entity."""
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_social()
        self.cancel_duo()
        self.cancel_council()
        self.cancel_shared_banana()
        for monkey in self.monkeys:
            monkey.configure(settings)
        self.set_count(settings.monkey_count)
        self.apply_profiles()
        self.set_chronicle_enabled(settings.chronicle_enabled)

    def set_mode(self, mode: str) -> None:
        if mode != 'MONKEY':
            self.cancel_city_life()
            self.cancel_expedition()
            self.cancel_duo()
            self.cancel_council()
            self.cancel_social()
        for monkey in self.monkeys:
            monkey.set_mode(mode)

    def set_behavior(self, behavior: str) -> None:
        """Set a persistent colony-level movement preference."""
        behavior = behavior if behavior in ("free", "follow") else "free"
        self.cancel_shared_banana()
        self.primary.settings.colony_behavior = behavior
        for monkey in self.monkeys:
            monkey.settings.colony_behavior = behavior
            monkey.set_colony_target(None)
            monkey._say("各自散步，自由发挥。" if behavior == "free" else "跟紧教授，排队前进！", 1.8)

    def set_collisions(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.primary.settings.collisions_enabled = enabled
        for monkey in self.monkeys:
            monkey.settings.collisions_enabled = enabled
            monkey.set_colony_target(None)
        if not enabled:
            self._collision_cooldowns.clear()
            self._relationship_cooldowns.clear()

    def drop_shared_banana(self) -> bool:
        """Spawn a visible banana token; the colony races to claim it."""
        if (self.count < 2 or self._race_active or not self.visible()
                or self.primary.focus.active or self.social.active or self.duo.active
                or self.council.active or self.expedition.active or self.city_life.active
                or any(p.paused or p.story.active or p._drag_active or p._social_active
                       for p in self.monkeys)):
            return False
        left, top, right, bottom = self.primary._work_area()
        token = BananaTokenOverlay(self.cancel_shared_banana)
        min_x = left + min(100, max(0, (right-left-token.width())/4))
        max_x = max(min_x, right-token.width()-min(100, max(0, (right-left-token.width())/4)))
        x = self._rng.uniform(min_x, max_x)
        y = max(top, bottom-token.height()-10)
        token.move(round(x), round(y))
        token.show()
        token.raise_()
        self._banana_token = token
        self._race_active = True
        for pet in self.monkeys:
            pet.set_colony_target(token.center_x - pet._sx - pet._size/2)
            pet._say("公共香蕉出现！冲啊！", 1.5)
        return True

    def cancel_shared_banana(self) -> None:
        token, self._banana_token = self._banana_token, None
        self._race_active = False
        if token is not None:
            token.hide()
            token.close()
            token.deleteLater()
        for pet in self.monkeys:
            pet.set_colony_target(None)

    def _claim_shared_banana(self, winner: MonkeyOverlay) -> None:
        if not self._race_active:
            return
        winner_name = winner.display_name
        self.cancel_shared_banana()
        winner.feed_banana()
        if self.quests is not None:
            self.quests.record('race')
            self.quests.record('feed')
        sharing = self.laws is not None and self.laws.active('banana_rules')
        winner._say((f"{winner_name} 抢到了香蕉，按条例分享！🍌"
                     if sharing else f"{winner_name} 抢到了公共香蕉！🍌"), 2.8)
        for pet in self.monkeys:
            if pet is not winner:
                if sharing:
                    pet.stats.mood = min(100.0, pet.stats.mood + 2.0)
                    pet._say(f"谢谢{winner_name}分享香蕉片！", 2.0)
                    if self.relationships is not None:
                        self.relationships.record_shared_activity(
                            winner.monkey_index, pet.monkey_index)
                else:
                    pet.stats.mood = max(-100.0, pet.stats.mood - 1.0)
                    pet._say(f"被{winner_name}抢先了！", 2.0)
                    if self.relationships is not None:
                        self.relationships.record_race(winner.monkey_index, pet.monkey_index)

    def _physics_tick(self, now: float) -> None:
        """Coordinate follower targets, a shared banana race, and soft contact."""
        if self.social.active or self.council.active or self.expedition.active or not self.primary.isVisible():
            return
        if any(p.paused for p in self.monkeys) or self.primary.focus.active:
            return

        bounds = self.primary._work_area()
        if self._race_active:
            if any(p.story.active or p._social_active or p._drag_active for p in self.monkeys):
                self.cancel_shared_banana()
                return
            token = self._banana_token
            if token is None or not token.isVisible():
                self.cancel_shared_banana()
                return
            target_center = token.center_x
            for pet in self.monkeys:
                if pet._drag_active or pet.story.active or pet._social_active or pet.body.airborne:
                    pet.set_colony_target(None)
                    continue
                personality_speed = {"trickster": 155.0, "scholar": 125.0, "sleepy": 88.0,
                                     "inventor": 135.0, "captain": 145.0, "shy": 105.0}.get(pet.personality, 125.0)
                target_x = clamp_x(target_center - pet._sx - pet._size/2,
                                   bounds, pet.width())
                pet.set_colony_target(target_x, personality_speed)
                sprite_center = pet.body.x + pet._sx + pet._size/2
                if abs(sprite_center-target_center) <= max(28.0, pet._size*0.22):
                    self._claim_shared_banana(pet)
                    return
            return

        behavior = self.primary.settings.colony_behavior
        if behavior == "follow" and self.count > 1:
            left, _top, right, _bottom = bounds
            left_space = max(0.0, self.primary.body.x-left)
            right_space = max(0.0, right-self.primary.width()-self.primary.body.x)
            direction = -1.0 if left_space >= right_space else 1.0
            available_space = max(left_space, right_space)
            gap = min(170.0, max(78.0, available_space/max(1,self.count-1)))
            for idx, pet in enumerate(self.monkeys):
                if (idx == 0 or pet._drag_active or pet.story.active or pet._social_active
                        or pet.body.airborne or now < pet._collision_reaction_until):
                    pet.set_colony_target(None)
                    continue
                target_x = clamp_x(self.primary.body.x + direction*gap*idx, bounds, pet.width())
                pet.set_colony_target(target_x, 82.0 if pet.personality == "sleepy" else 102.0)
        else:
            for pet in self.monkeys:
                pet.set_colony_target(None)

        if not self.primary.settings.collisions_enabled:
            return
        active = [p for p in self.monkeys if p.isVisible() and not p._drag_active
                  and not p.story.active and not p._social_active and not p.body.airborne]
        for i, a in enumerate(active):
            for b in active[i+1:]:
                dx = (b.body.x+b._sx+b._size/2) - (a.body.x+a._sx+a._size/2)
                pair = tuple(sorted((id(a), id(b))))
                collided = resolve_horizontal_collision(
                    a.body, b.body,
                    center_offset_a=a._sx+a._size/2,
                    center_offset_b=b._sx+b._size/2,
                    half_width_a=a._size*0.36,
                    half_width_b=b._size*0.36,
                    center_y_a=a.body.y+a._sy+a._size/2,
                    center_y_b=b.body.y+b._sy+b._size/2,
                    half_height_a=a._size*0.38,
                    half_height_b=b._size*0.38,
                )
                if not collided:
                    continue
                a.body.x = clamp_x(a.body.x, bounds, a.width())
                b.body.x = clamp_x(b.body.x, bounds, b.width())
                for pet in (a,b):
                    xy=(round(pet.body.x),round(pet.body.y))
                    if xy != pet._last_move:
                        pet.move(*xy)
                        pet._last_move=xy
                if now >= self._collision_cooldowns.get(pair, 0.0):
                    self._collision_cooldowns[pair] = now + 1.5
                    a.react_to_colony_collision(b.display_name, -1 if dx >= 0 else 1)
                    b.react_to_colony_collision(a.display_name, 1 if dx >= 0 else -1)
                    if self.relationships is not None and now >= self._relationship_cooldowns.get(pair, 0.0):
                        self.relationships.record_collision(a.monkey_index, b.monkey_index)
                        self._relationship_cooldowns[pair] = now + 20.0

    def _social_tick(self) -> None:
        now = time.monotonic()
        dt = min(.25, max(0., now-self._last_social_tick))
        self._last_social_tick = now
        if (not self.primary.isVisible() or any(p.paused for p in self.monkeys)
                or self.primary.focus.active):
            if self.social.active:
                self.cancel_social()
            if self.duo.active:
                self.cancel_duo()
            if self.council.active:
                self.cancel_council()
            if self.expedition.active:
                self.cancel_expedition()
            if self.city_life.active:
                self.cancel_city_life()
            return
        if self.city_life.active:
            plan = self.city_life.plan
            attendees = [self.monkeys[i] for i in (plan.first, plan.second)
                         if i < self.count]
            if (len(attendees) != 2 or
                    any(p._drag_active or p.story.active or
                        not p._social_active or not p.isVisible()
                        for p in attendees)):
                self.cancel_city_life()
            elif self.city_life.advance(dt):
                if self.city_life.finished:
                    self._complete_city_life()
                    self.cancel_city_life()
                else:
                    self._apply_city_life_beat()
            return
        if self.expedition.active:
            plan = self.expedition.plan
            attendees = [self.monkeys[m.index] for m in plan.crew if m.index < self.count]
            if (len(attendees) != len(plan.crew) or
                    any(p._drag_active or p.story.active or not p._social_active
                        or not p.isVisible() for p in attendees)):
                self.cancel_expedition()
            elif self.expedition.advance(dt):
                if self.expedition.finished:
                    self._complete_expedition()
                    self.cancel_expedition()
                else:
                    self._apply_expedition_beat()
            return
        if self.council.active:
            plan = self.council.plan
            attendees = [self.monkeys[s.index] for s in plan.seats
                         if s.index < self.count]
            if (len(attendees) != len(plan.seats) or
                    any(p._drag_active or p.story.active or not p._social_active
                        or not p.isVisible() for p in attendees)):
                self.cancel_council()
            elif self.council.advance(dt):
                if self.council.finished:
                    self._complete_council()
                    self.cancel_council()
                else:
                    self._apply_council_beat()
            return
        self._physics_tick(now)
        if self.duo.active:
            event = self.duo.event
            members = [p for p in self.monkeys
                       if p.monkey_index in (event.first, event.second)]
            if (len(members) != 2 or any(
                    p._drag_active or p.story.active or not p._social_active
                    for p in members)):
                self.cancel_duo()
            elif self.duo.advance(dt):
                if self.duo.finished:
                    self._complete_duo()
                    self.cancel_duo()
                else:
                    self._apply_duo_beat()
        if (not self.social.active and not self.duo.active and not self._race_active and self.count >= 2
                and not (self.laws is not None and self.laws.active('quiet_hours'))
                and self.primary.settings.ambient_encounters
                and self.primary.settings.mode == "MONKEY"):
            self._maybe_encounter(now)
        if self.social.active:
            if any(p._drag_active or p.story.active or not p._social_active for p in self.monkeys):
                self.cancel_social()
            else:
                completed_name = self.social.name
                if self.social.advance(dt):
                    if self.social.active:
                        self._apply_group_beat()
                    else:
                        self._complete_social(completed_name)
                        self._release_group_poses()
            return
        if (self.count >= 2 and self.primary.settings.social_enabled
                and not self.duo.active and self.primary.settings.mode == 'MONKEY'
                and not (self.laws is not None and self.laws.active('quiet_hours'))
                and now >= self._next_social_at):
            self.start_social(self._rng.choice(('meeting', 'banana_duel')))
        if now >= self._next_social_at:
            self._next_social_at = now + 300

    def start_city_life(self, case_id: str, first: int, second: int,
                        choice: str) -> bool:
        """Manually play the next uncompleted chapter of an owned building."""
        if (self.expeditions is None or self.count < 2 or
                self.city_life.active or self.council.active or self.expedition.active
                or self.duo.active or self.social.active or self._race_active
                or self.primary.focus.active or not self.primary.isVisible()
                or any(p.paused for p in self.monkeys)):
            return False
        if (type(case_id) is not str or case_id not in CASE_TITLES or
                case_id not in self.expeditions.buildings or
                type(first) is not int or type(second) is not int or
                first == second or not 0 <= first < self.count or
                not 0 <= second < self.count):
            return False
        pair = (self.monkeys[first], self.monkeys[second])
        if any(not pet.isVisible() or pet._drag_active or pet.story.active
               or pet._social_active or pet.body.airborne or pet._demo_enabled
               for pet in pair):
            return False
        values = self.relationships.get(first, second) if self.relationships else {}
        try:
            plan = prepare_city_case(
                case_id, self.expeditions.city_cases[case_id], first, second,
                choice, bond=values.get('bond', 0), trust=values.get('trust', 0),
                first_personality=pair[0].personality,
                second_personality=pair[1].personality)
        except ValueError:
            return False
        if not self.city_life.start(plan):
            return False
        left, top, right, bottom = self.primary._work_area()
        available = max(0., right-left-max(p.width() for p in pair))
        for n, pet in enumerate(pair):
            new_x = left + available*n
            pet.set_colony_target(None)
            pet.body.x = max(left, min(right-pet.width(), new_x))
            pet.body.y = max(top, bottom-pet.height())
            pet.body.vx = pet.body.vy = 0.
            pet.body.airborne = False
            pet.move(round(pet.body.x), round(pet.body.y))
            pet._last_move = (round(pet.body.x), round(pet.body.y))
        self._last_social_tick = time.monotonic()
        self._apply_city_life_beat()
        return True

    def _apply_city_life_beat(self) -> None:
        beat = self.city_life.beat
        if beat is None:
            return
        for index, action, speech in beat.poses:
            if index < self.count:
                self.monkeys[index].social_pose(action, speech)

    def _complete_city_life(self) -> None:
        if not self.city_life.consume_completion():
            return
        plan = self.city_life.plan
        if (plan is None or self.expeditions is None or
                not self.expeditions.record_city_chapter(plan)):
            return
        # Relationship fallout affects later chapters' endings; persistence
        # is only after the completed chapter has been committed exactly once.
        if self.relationships is not None:
            if plan.choice == 'careful':
                self.relationships.record_shared_activity(plan.first, plan.second)
            else:
                self.relationships.record_collision(plan.first, plan.second)
            if plan.ending == 'reconciled':
                self.relationships.reconcile(plan.first, plan.second)
            elif plan.ending == 'chaos':
                self.relationships.record_race(plan.first, plan.second)
        if self.quests is not None:
            self.quests.record('group')

    def cancel_city_life(self) -> None:
        if not self.city_life.active:
            return
        pair = (self.city_life.plan.first, self.city_life.plan.second)
        self.city_life.cancel()
        for index in pair:
            if index < self.count:
                self.monkeys[index].exit_social()
        self._next_social_at = time.monotonic() + self._rng.uniform(240, 420)

    def start_expedition(self, mission: str, indices: tuple[int, ...]) -> bool:
        """Manually stage a 2-6 member fictional exploration, never in background."""
        if (self.expeditions is None or self.count < 2 or self.social.active
                or self.duo.active or self.council.active or self.expedition.active
                or self.city_life.active
                or self._race_active or self.primary.focus.active
                or not self.primary.isVisible() or any(p.paused for p in self.monkeys)):
            return False
        if (type(indices) is not tuple or not 2 <= len(indices) <= self.count
                or any(type(i) is not int or not 0 <= i < self.count for i in indices)
                or len(set(indices)) != len(indices)):
            return False
        team = [self.monkeys[i] for i in indices]
        if any(not pet.isVisible() or pet._drag_active or pet.story.active
               or pet._social_active or pet.body.airborne or pet._demo_enabled for pet in team):
            return False
        policies = frozenset(key for key in ('banana_rules', 'rocket_license', 'quiet_hours')
                             if self.laws is not None and self.laws.active(key))
        roster = tuple(Explorer(p.monkey_index, p.personality) for p in team)
        try:
            plan = plan_expedition(
                mission, roster, self.relationships, policies,
                self.expeditions.buildings)
        except ValueError:
            return False
        if not self.expedition.start(plan):
            return False
        left, top, right, bottom = self.primary._work_area()
        width = max(p.width() for p in team)
        for n, pet in enumerate(team):
            new_x = left + max(0, right-left-width)*n/max(1, len(team)-1)
            pet.set_colony_target(None)
            pet.body.x = max(left, min(right-pet.width(), new_x))
            pet.body.y = max(top, bottom-pet.height())
            pet.body.vx = pet.body.vy = 0.
            pet.body.airborne = False
            pet.move(round(pet.body.x), round(pet.body.y))
            pet._last_move = (round(pet.body.x), round(pet.body.y))
        self._last_social_tick = time.monotonic()
        self._apply_expedition_beat()
        return True

    def _apply_expedition_beat(self) -> None:
        beat = self.expedition.beat
        if beat is None:
            return
        for index, action, speech in beat.poses:
            if 0 <= index < self.count:
                self.monkeys[index].social_pose(action, speech)

    def _complete_expedition(self) -> None:
        if not self.expedition.consume_completion():
            return
        plan = self.expedition.plan
        if plan is None or self.expeditions is None or not self.expeditions.record(plan):
            return
        if self.relationships is not None:
            self.relationships.record_expedition(
                tuple(person.index for person in plan.crew), plan.outcome)
        if (self.chronicle is not None and plan.outcome == 'success'
                and len(plan.crew) >= 2):
            trigger = {'banana_scout': 'banana_duel', 'meteor_lab': 'launch',
                       'village_repair': 'meeting'}.get(plan.mission)
            if trigger is not None:
                self.chronicle.observe(trigger, plan.crew[0].index, plan.crew[1].index)
        if self.quests is not None:
            self.quests.record('group')

    def cancel_expedition(self) -> None:
        if not self.expedition.active:
            return
        crew = [p.index for p in self.expedition.plan.crew]
        self.expedition.cancel()
        for idx in crew:
            if idx < self.count:
                self.monkeys[idx].exit_social()
        self._next_social_at = time.monotonic() + self._rng.uniform(240, 420)

    def clear_expeditions(self) -> None:
        self.cancel_city_life()
        self.cancel_expedition()
        if self.expeditions is not None:
            # Clearing the save invalidates construction ownership: remove
            # previously displayed building props but preserve free furniture.
            for prop in list(self.furniture):
                if prop.kind in BUILDINGS:
                    self.remove_furniture(prop)
            self.expeditions.clear()

    def start_council(self, issue: str, indices: tuple[int, ...]) -> bool:
        """Stage a user-requested 3-6 monkey vote; no auto polling or user profiling."""
        if (self.count < 3 or self.social.active or self.duo.active
                or self.council.active or self.expedition.active
                or self.city_life.active or self._race_active
                or self.primary.focus.active or not self.primary.isVisible()
                or any(p.paused for p in self.monkeys)):
            return False
        if (not isinstance(indices, tuple) or not 3 <= len(indices) <= self.count
                or any(type(i) is not int or not 0 <= i < self.count
                       for i in indices) or len(set(indices)) != len(indices)):
            return False
        people = [self.monkeys[i] for i in indices]
        if any(not p.isVisible() or p._drag_active or p.story.active or
               p._social_active or p.body.airborne or p._demo_enabled
               for p in people):
            return False
        seats = tuple(Seat(i, self.monkeys[i].personality) for i in indices)
        try:
            plan = prepare_council(issue, seats, self.relationships)
        except ValueError:
            return False
        if not self.council.start(plan):
            return False
        # Gather only attendees; all other monkeys retain their own positions.
        left, top, right, bottom = self.primary._work_area()
        widest = max(p.width() for p in people)
        available = max(0., right-left-widest)
        for n, pet in enumerate(people):
            pos_x = left + available*n/max(1, len(people)-1)
            pet.set_colony_target(None)
            pet.body.x = max(left, min(right-pet.width(), pos_x))
            pet.body.y = max(top, bottom-pet.height())
            pet.body.vx = pet.body.vy = 0.
            pet.body.airborne = False
            pet.move(round(pet.body.x), round(pet.body.y))
            pet._last_move = (round(pet.body.x), round(pet.body.y))
        self._last_social_tick = time.monotonic()
        self._apply_council_beat()
        return True

    def _apply_council_beat(self) -> None:
        beat = self.council.beat
        if beat is None:
            return
        for index, action, phrase in beat.poses:
            if index < self.count:
                self.monkeys[index].social_pose(action, phrase)

    def _complete_council(self) -> None:
        if not self.council.consume_completion():
            return
        plan = self.council.plan
        if plan is None:
            return
        if self.relationships is not None:
            self.relationships.record_council(plan.votes)
        if self.laws is not None:
            self.laws.enact(plan.issue, plan.result)
        # Only an explicitly enabled fictional chronicle can create a case.
        if self.chronicle is not None and self.chronicle.enabled:
            self.chronicle.observe('meeting', plan.seats[0].index,
                                   plan.seats[1].index)
        if self.quests is not None:
            self.quests.record('group')

    def cancel_council(self) -> None:
        if not self.council.active:
            return
        indices = [s.index for s in self.council.plan.seats]
        self.council.cancel()
        for index in indices:
            if index < self.count:
                self.monkeys[index].exit_social()
        self._next_social_at = time.monotonic() + self._rng.uniform(240, 420)

    def _participants(self) -> list[Participant]:
        """Only inspect our own character coordinates and busy flags."""
        return [Participant(
            index=p.monkey_index,
            x=p.body.x + p._sx + p._size/2,
            y=p.body.y + p._sy + p._size/2,
            personality=p.personality,
            busy=bool(p.story.active or p._social_active or p._drag_active or
                      p.body.airborne or p._demo_enabled),
        ) for p in self.monkeys]

    def _play_encounter(self, event: Encounter) -> None:
        """Begin a finite two-beat scene. No relationship effect until finished."""
        if self.duo.start(event):
            self._apply_duo_beat()

    def _apply_duo_beat(self) -> None:
        event, beat = self.duo.event, self.duo.beat
        if event is None or beat is None:
            return
        for index, (action, phrase) in ((event.first, beat.first), (event.second, beat.second)):
            pet = next((p for p in self.monkeys if p.monkey_index == index), None)
            if pet is not None:
                pet.social_pose(action, phrase)

    def _complete_duo(self) -> None:
        # Do not commit a still-playing or cancelled two-beat incident.
        if not self.duo.finished:
            return
        event = self.duo.event
        if event is None:
            return
        if self._active_chapter is not None:
            chapter = self._active_chapter
            if self.chronicle is not None and self.chronicle.complete(chapter):
                # Follow-up fiction changes relationships only on completed beats.
                if self.relationships is not None:
                    if chapter.branch == 'chaos' and chapter.chapter == 2:
                        self.relationships.record_collision(event.first, event.second)
                    else:
                        self.relationships.record_shared_activity(event.first, event.second)
            return
        if self.relationships is not None:
            if event.kind in ('debate', 'inspection'):
                self.relationships.record_collision(event.first, event.second)
            elif event.kind == 'prank':
                self.relationships.record_race(event.first, event.second)
            else:
                self.relationships.record_shared_activity(event.first, event.second)
        if self.chronicle is not None:
            self.chronicle.observe(event.kind, event.first, event.second)

    def cancel_duo(self) -> None:
        self._active_chapter = None
        if not self.duo.active:
            return
        self.duo.cancel()
        for pet in self.monkeys:
            pet.exit_social()

    def play_chronicle_chapter(self, case_id: int) -> bool:
        """A user action only; never automatically opens another chapter."""
        if (self.chronicle is None or not self.chronicle.enabled or self.count < 2
                or self.duo.active or self.council.active or self.expedition.active
                or self.city_life.active or self.social.active or self._race_active
                or not self.visible() or self.primary.focus.active
                or any(p.paused for p in self.monkeys)):
            return False
        case = next((c for c in self.chronicle.pending(member_count=self.count)
                     if c['id'] == case_id), None)
        if case is None:
            return False
        first, second = case['first'], case['second']
        participants = self._participants()
        if (any(participants[index].busy for index in (first, second)) or
                any(not self.monkeys[index].isVisible() for index in (first, second))):
            return False
        relation = self.relationships.get(first, second) if self.relationships else {}
        chapter = self.chronicle.preview(case_id, relation)
        if chapter is None:
            return False
        event = Encounter(first, second, 'chronicle',
                          chapter.opening[0][0], chapter.opening[1][0],
                          chapter.opening[0][1], chapter.opening[1][1],
                          outcome_first=chapter.ending[0],
                          outcome_second=chapter.ending[1])
        if not self.duo.start(event):
            return False
        self._active_chapter = chapter
        self._apply_duo_beat()
        return True

    def set_chronicle_enabled(self, enabled: bool) -> None:
        if not enabled and self._active_chapter is not None:
            self.cancel_duo()
        if self.chronicle is not None:
            self.chronicle.enabled = bool(enabled)
        self.primary.settings.chronicle_enabled = bool(enabled)
        for pet in self.monkeys:
            pet.settings.chronicle_enabled = bool(enabled)


    def _maybe_encounter(self, now: float, *, force: bool = False,
                         pair: tuple[int, int] | None = None) -> bool:
        if (self.count < 2 or self.social.active or self.duo.active or self.council.active or self.expedition.active or self.city_life.active or self._race_active or
                not self.visible() or self.primary.focus.active or
                any(p.paused for p in self.monkeys)):
            return False
        participants = self._participants()
        if pair is not None:
            # Reject duplicates, booleans, invalid or hidden members.
            if (len(pair) != 2 or any(type(i) is not int or not 0 <= i < self.count
                                      for i in pair) or pair[0] == pair[1]):
                return False
            participants = [p for p in participants
                            if p.index in pair and self.monkeys[p.index].isVisible()]
            if len(participants) != 2:
                return False
        event = self.encounters.choose(now, participants, self.relationships,
                                       force=force)
        if event is None:
            return False
        self._play_encounter(event)
        return True

    def demo_encounter(self) -> bool:
        """Manually trigger the closest available pair even if auto mode is off."""
        return self._maybe_encounter(time.monotonic(), force=True)

    def demo_pair(self, first: int, second: int) -> bool:
        """User-selected pair: bypass distance/cooldowns, never busy-state checks."""
        return self._maybe_encounter(time.monotonic(), force=True, pair=(first, second))

    def set_ambient_encounters(self, enabled: bool) -> None:
        if not enabled:
            self.cancel_duo()
        self.primary.settings.ambient_encounters = bool(enabled)
        for pet in self.monkeys:
            pet.settings.ambient_encounters = bool(enabled)
        # Turning the feature off never leaves stale pending work or active timers.
        self.encounters.clear()

    def _apply_group_beat(self) -> None:
        beat = self.social.beat
        if beat is None:
            return
        if self.social.name == 'rocket_trial':
            # Give lead engineer dialogue to the actual inventor, regardless
            # of which monkey index that character occupies.
            lead = next((i for i, pet in enumerate(self.monkeys)
                         if pet.personality == 'inventor'), 0)
            assistant = next((i for i, pet in enumerate(self.monkeys)
                              if i != lead and pet.personality == 'captain'),
                             next(i for i in range(self.count) if i != lead))
        else:
            lead, assistant = 0, 1
        for index, pet in enumerate(self.monkeys):
            action, phrase = (beat.first if index == lead else
                              beat.second if index == assistant else beat.others)
            pet.social_pose(action, phrase)

    def _release_group_poses(self) -> None:
        for pet in self.monkeys:
            pet.exit_social()
        self._next_social_at = time.monotonic() + self._rng.uniform(240, 420)

    def cancel_social(self) -> None:
        self.social.cancel()
        self._release_group_poses()

    def start_rocket_trial(self) -> bool:
        """Manual fictional rocket trial, unlocked only by a completed vote."""
        if (self.laws is None or not self.laws.active('rocket_license')
                or self.count < 3 or self.council.active or self.duo.active
                or self.social.active or self._race_active
                or not any(p.personality == 'inventor' for p in self.monkeys)):
            return False
        return self.start_social('rocket_trial')

    def clear_monkey_laws(self) -> None:
        """Reset fictional policies without touching relationships or chronicle."""
        if self.social.name == 'rocket_trial':
            self.cancel_social()
        if self.laws is not None:
            self.laws.clear()

    def start_social(self, name: str) -> bool:
        # No direct-call bypass of an unapproved in-universe trial.
        if name == 'rocket_trial' and (self.laws is None or not self.laws.active('rocket_license')):
            return False
        if (self.council.active or self.expedition.active or self.city_life.active
                or self.count < 2 or not self.visible() or self.primary.focus.active
                or any(p.paused or p.story.active or p._drag_active for p in self.monkeys)):
            return False
        if not self.social.start(name, self.count):
            return False
        self.cancel_duo()
        self.cancel_shared_banana()
        # Assemble on the same screen; no cursor movement or other window control.
        self.gather_for_meeting()
        self._last_social_tick = time.monotonic()
        self._apply_group_beat()
        return True

    def _complete_social(self, name: str) -> None:
        """Commit social effects only after a group story reaches its ending."""
        indices = [pet.monkey_index for pet in self.monkeys]
        inventor = next((p.monkey_index for p in self.monkeys
                         if p.personality == 'inventor'), indices[0])
        partner = next((p.monkey_index for p in self.monkeys
                        if p.monkey_index != inventor and p.personality == 'captain'),
                       next((i for i in indices if i != inventor), indices[0]))
        if self.chronicle is not None and len(indices) >= 2:
            if name == 'rocket_trial':
                self.chronicle.observe(name, inventor, partner)
            else:
                self.chronicle.observe(name, indices[0], indices[1])
        if self.relationships is not None:
            if name == 'meeting':
                self.relationships.record_meeting(indices)
            elif name == 'banana_duel' and len(indices) >= 2:
                self.relationships.record_race(indices[0], indices[1])
            elif name == 'rocket_trial':
                self.relationships.record_shared_activity(inventor, partner)
        if self.quests is not None and name in ('meeting', 'rocket_trial'):
            self.quests.record('group')
        if self.primary.history is not None:
            self.primary.history.add(name)

    def place_furniture(self, kind: str) -> bool:
        """Place a draggable prop on desktop, or an actually constructed building."""
        if kind not in PROPS or len(self.furniture) >= 8:
            return False
        if (kind in BUILDINGS and
                (self.expeditions is None or kind not in self.expeditions.buildings)):
            return False
        if kind in BUILDINGS and any(p.kind == kind for p in self.furniture):
            return False
        bounds = self.primary._work_area()
        index = len(self.furniture)
        widget = FurnitureWidget(kind, self._interact_furniture, self.remove_furniture,
                                 always_on_top=self.primary.settings.always_on_top)
        left, top, right, bottom = bounds
        columns = max(1, int(max(1, right-left) // 150))
        x = left + 28 + (index % columns) * 142
        y = max(top + 24, bottom - widget.height() - 160 - (index // columns) * 112)
        widget.move(min(x, max(left, right-widget.width())), min(y, max(top, bottom-widget.height())))
        self.furniture.append(widget)
        widget.show()
        return True

    def display_city_building(self, key: str) -> bool:
        """Only completed structures can be displayed as physical Qt props."""
        if (type(key) is not str or key not in BUILDINGS or
                self.expeditions is None or key not in self.expeditions.buildings):
            return False
        existing = next((prop for prop in self.furniture if prop.kind == key), None)
        if existing is not None:
            existing.show()
            existing.raise_()
            return True
        return self.place_furniture(key)

    def remove_furniture(self, widget: FurnitureWidget) -> None:
        if widget in self.furniture:
            self.furniture.remove(widget)
        widget.hide()
        widget.close()
        widget.deleteLater()

    def clear_furniture(self) -> None:
        for widget in list(self.furniture):
            self.remove_furniture(widget)

    def _interact_furniture(self, widget: FurnitureWidget) -> None:
        if self.primary.focus.active or any(p.paused for p in self.monkeys):
            self.primary._say('专注或暂停期间，家具暂不互动。')
            return
        if widget.kind == 'banana_tree':
            if self.count > 1:
                if not self.drop_shared_banana():
                    self.primary._say('猴子们现在太忙，稍后再来摘香蕉。')
            else:
                if self.primary.feed_banana() and self.quests is not None:
                    self.quests.record('feed')
            return
        if widget.kind in ('blackboard', 'mirror'):
            target = self.primary
            if target.start_story('blackboard' if widget.kind == 'blackboard' else 'mirror'):
                if self.quests is not None:
                    self.quests.record('story')
            else:
                target._say('教授正在处理另一场事故。')
            return
        center_x = widget.x() + widget.width()/2
        center_y = widget.y() + widget.height()/2
        target = min(self.monkeys, key=lambda pet: (pet.body.x+pet._sx+pet._size/2-center_x)**2 +
                     (pet.body.y+pet._sy+pet._size/2-center_y)**2)
        if target.story.active or target._social_active or target._drag_active:
            target._say('现在没空，等这场事故结束。')
            return
        if widget.kind in BUILDINGS:
            if (self.expeditions is None or
                    widget.kind not in self.expeditions.buildings):
                self.remove_furniture(widget)
                return
            stories = {
                'banana_vault': ('eat_banana', '香蕉仓库盘点完成，全部属于猴山！🍌'),
                'galaxy_scope': ('blink', '银河望远镜发现了新星！下一次科研出发！🔭'),
                'public_square': ('wake', '猴山广场竣工，居民们欢迎你！🏛️'),
                'monkey_academy': ('wake', '联合实验室开课！猴山文明万岁！🌌'),
            }
            action, phrase = stories[widget.kind]
            target.play_action(action)
            target._say(phrase, 2.7)
            if self._on_city_event_open is not None:
                self._on_city_event_open(widget.kind)
            return
        if widget.kind == 'trampoline':
            target.play_action('fall')
            target.body.throw(0, -560)
            target._say('蹦床起飞！这不属于学术论文。', 2.5)
        elif widget.kind == 'chair':
            target.play_action('sleep')
            target._say('教授专座已被占领。闲人免进。', 2.5)

    def toggle_pause(self, enabled: bool) -> None:
        if enabled:
            self.cancel_city_life()
            self.cancel_expedition()
            self.cancel_duo()
            self.cancel_council()
            self.cancel_social()
        for monkey in self.monkeys:
            monkey.toggle_pause(enabled)

    def set_topmost(self, enabled: bool) -> None:
        from PySide6.QtCore import Qt
        for prop in self.furniture:
            visible_prop = prop.isVisible()
            prop.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
            if visible_prop:
                prop.show()
        for monkey in self.monkeys:
            monkey.settings.always_on_top = enabled
            visible = monkey.isVisible()
            monkey.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
            if visible:
                monkey.show()
                monkey.reapply_hit_region()

    def show_all(self) -> None:
        for monkey in self.monkeys:
            monkey.show()
            monkey.reapply_hit_region()
        for prop in self.furniture:
            prop.show()

    def hide_all(self) -> None:
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_council()
        self.cancel_duo()
        self.cancel_social()
        self.cancel_shared_banana()
        for monkey in self.monkeys:
            monkey.hide()
        for prop in self.furniture:
            prop.hide()

    def visible(self) -> bool:
        return any(monkey.isVisible() for monkey in self.monkeys)

    def gather(self) -> None:
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_council()
        self.cancel_duo()
        self.cancel_shared_banana()
        if self.social.active and any(p._social_active for p in self.monkeys):
            self.cancel_social()
        """Return every pet to a visible row, without overlapping them all."""
        for idx, monkey in enumerate(self.monkeys):
            point = spawn_position(self.primary._work_area(),
                                   (monkey.width(), monkey.height()), idx, self.count)
            monkey.story.cancel()
            monkey.body.x, monkey.body.y = map(float, point)
            monkey.body.vx = monkey.body.vy = 0
            monkey.body.airborne = False
            monkey.move(*point)
        self.show_all()

    def gather_for_meeting(self) -> None:
        """Place the participants close enough that the synchronized scene reads as one."""
        left, top, right, bottom = self.primary._work_area()
        maximum_width = max(p.width() for p in self.monkeys)
        gap = min(188.0, max(0., (right-left-maximum_width-24)/max(1,self.count-1)))
        total = maximum_width + (self.count-1)*gap
        start = max(left, left + (right-left-total)/2)
        for i, monkey in enumerate(self.monkeys):
            monkey.story.cancel()
            monkey.body.vx = monkey.body.vy = 0
            monkey.body.airborne = False
            monkey.body.x = max(left, min(right-monkey.width(), start+i*gap))
            monkey.body.y = max(top,bottom-monkey.height())
            monkey.move(round(monkey.body.x), round(monkey.body.y))
            monkey._last_move = (round(monkey.body.x),round(monkey.body.y))
        self.show_all()

    def prepare_focus(self) -> None:
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_council()
        self.cancel_duo()
        self.cancel_shared_banana()
        self.cancel_social()
        """Cancel old stories as soon as primary activates a focus session."""
        for monkey in self.monkeys[1:]:
            monkey.story.cancel()
            monkey.toggle_demo(False)
            monkey.body.vx = 0
            monkey.stats.action = 'idle'
            monkey.player.request('idle', force=True, restart=True)
            monkey._set_current_sprite(force=True)

    def quit_all(self) -> None:
        self._social_timer.stop()
        self.cancel_city_life()
        self.cancel_expedition()
        self.cancel_council()
        self.cancel_duo()
        self.cancel_shared_banana()
        self.cancel_social()
        self.clear_furniture()
        for monkey in self.monkeys:
            monkey.story.cancel()
            monkey._timer.stop()
            monkey.audio.set_enabled(False)
            monkey.close()
