"""Deterministic sprite animation state machine; no Qt or graphics dependency.

A state is a series of on-disk frame names plus behavior metadata. The
manager owns no GUI objects, making it easy to test and safe to pause.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnimationSpec:
    name: str
    frames: tuple[str, ...]
    fps: float
    loop: bool
    priority: int
    interruptible: bool
    next_action: str = "idle"
    anchor: tuple[float, float] = (0.5, 0.96)

    def __post_init__(self) -> None:
        if not self.frames or self.fps <= 0 or not math.isfinite(self.fps):
            raise ValueError(f"{self.name}: a finite, positive fps and frames are required")
        if self.priority < 0 or not all(math.isfinite(v) and 0 <= v <= 1 for v in self.anchor):
            raise ValueError(f"{self.name}: priority / normalized anchor invalid")


def load_manifest(path: Path) -> dict[str, AnimationSpec]:
    """Parse and validate relative paths, transition targets and shared anchor."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 2:
        raise ValueError("Animation manifest schema v2 required")
    spec_map: dict[str, AnimationSpec] = {}
    for name, item in raw["states"].items():
        if not item.get("implemented", False):
            continue
        paths = tuple(item.get("frames", ()))
        for frame in paths:
            if not isinstance(frame, str) or "\\" in frame or ":" in frame or "\x00" in frame:
                raise ValueError(f"Unsafe/invalid sprite path: {frame!r}")
            part = Path(frame)
            if part.is_absolute() or ".." in part.parts or part.suffix.lower() != ".png":
                raise ValueError(f"Unsafe/invalid sprite path: {frame!r}")
        spec_map[name] = AnimationSpec(
            name=name,
            frames=paths,
            fps=float(item["fps"]),
            loop=bool(item["loop"]),
            priority=int(item["priority"]),
            interruptible=bool(item["interruptible"]),
            next_action=item.get("next_action", "idle"),
            anchor=tuple(item.get("anchor_normalized", raw["anchor_normalized"])),
        )
    if "idle" not in spec_map:
        raise ValueError("The idle animation is mandatory")
    anchors = {s.anchor for s in spec_map.values()}
    if len(anchors) != 1:
        raise ValueError("All states must use the same fixed canvas anchor")
    for spec in spec_map.values():
        if spec.next_action not in spec_map:
            raise ValueError(f"{spec.name}: unknown next_action {spec.next_action}")
    return spec_map


class AnimationPlayer:
    def __init__(self, specs: dict[str, AnimationSpec]) -> None:
        if "idle" not in specs:
            raise ValueError("idle state is required")
        self.specs = dict(specs)
        self.action = "idle"
        self.frame_index = 0
        self.frame_elapsed = 0.0
        self.facing = 1  # +1 means source facing, -1 horizontal mirror
        self.paused = False

    @property
    def frame_path(self) -> str:
        return self.specs[self.action].frames[self.frame_index]

    def face(self, direction: int) -> None:
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        self.facing = direction

    def request(self, name: str, *, force: bool = False, restart: bool = False) -> bool:
        """Request an action without violating locked actions or priority.

        An unknown action uses safe idle fallback; deliberate user/demo
        commands pass force=True, bypassing the normal autonomous policy.
        """
        if name not in self.specs:
            name = "idle"
        if name == self.action and not restart:
            return True
        current, wanted = self.specs[self.action], self.specs[name]
        if not force and (not current.interruptible or wanted.priority < current.priority):
            return False
        self.action, self.frame_index, self.frame_elapsed = name, 0, 0.0
        return True

    def advance(self, seconds: float) -> bool:
        """Tick by elapsed monotonic time; returns whether the visible frame changed.

        Terminal animations automatically return to their configured next
        state. Timing uses seconds, never wall clock or tick counts.
        """
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("delta must be finite and nonnegative")
        if self.paused or seconds == 0:
            return False
        before = (self.action, self.frame_index)
        remaining = seconds
        # A deliberately bounded number of transitions, even for giant deltas.
        # This avoids pathological loops and pauses/hiccups playing many stories.
        for _ in range(32):
            spec = self.specs[self.action]
            duration = len(spec.frames) / spec.fps
            total = self.frame_elapsed + self.frame_index / spec.fps + remaining
            if spec.loop:
                pos = total % duration
                self.frame_index = min(int((pos + 1e-10) * spec.fps), len(spec.frames) - 1)
                self.frame_elapsed = pos - self.frame_index / spec.fps
                break
            if total + 1e-10 < duration:
                self.frame_index = min(int((total + 1e-10) * spec.fps), len(spec.frames) - 1)
                self.frame_elapsed = max(0.0, total - self.frame_index / spec.fps)
                break
            remaining = max(0.0, total - duration)
            self.action = spec.next_action
            self.frame_index = 0
            self.frame_elapsed = 0.0
        else:
            self.action, self.frame_index, self.frame_elapsed = "idle", 0, 0.0
        return (self.action, self.frame_index) != before


# Fixed demo only: P05 will replace this with autonomous behavior decisions.
DEMO_STEPS: tuple[tuple[str, float], ...] = (
    ("idle", 2.5), ("blink", 0.42), ("walk", 2.8), ("turn", 0.70),
    ("sleep", 2.4), ("wake", 0.75), ("fall", 0.85), ("get_up", 0.90),
)


class DemoTimeline:
    """Small non-intelligent animation tour for P02 testing."""

    def __init__(self, steps: tuple[tuple[str, float], ...] = DEMO_STEPS) -> None:
        if not steps or any(s <= 0 for _, s in steps):
            raise ValueError("Demo timeline requires positive durations")
        self.steps = steps
        self.step_index = 0
        self.elapsed = 0.0

    def reset(self) -> None:
        self.step_index = 0
        self.elapsed = 0.0

    def advance(self, delta: float) -> str | None:
        if not math.isfinite(delta) or delta < 0:
            raise ValueError("delta must be finite and nonnegative")
        self.elapsed += delta
        new_action = None
        for _ in range(128):
            duration = self.steps[self.step_index][1]
            if self.elapsed + 1e-10 < duration:
                break
            self.elapsed -= duration
            self.step_index = (self.step_index + 1) % len(self.steps)
            new_action = self.steps[self.step_index][0]
        else:
            # Drop severe timer stalls instead of spending seconds replaying.
            self.reset()
            new_action = self.steps[0][0]
        return new_action
