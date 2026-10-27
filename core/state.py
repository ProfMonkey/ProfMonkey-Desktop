"""Non-invasive autonomous behavior and mood. Seeded for repeatable tests."""
from dataclasses import dataclass
import random


@dataclass
class PetState:
    energy: float = 70
    mood: float = 15
    curiosity: float = 60
    mischief: float = 45
    action: str = 'idle'
    mode: str = 'QUIET'

    def tick(self, dt: float) -> None:
        if self.action == 'sleep':
            self.energy = min(100, self.energy + 5.0 * dt)
        elif self.action in ('walk', 'turn'):
            self.energy = max(0, self.energy - 1.8 * dt)
        elif self.action == 'run':
            self.energy = max(0, self.energy - 3.5 * dt)
        else:
            self.energy = min(100, self.energy + 0.13 * dt)
        self.mood *= (1.0 - min(.01 * dt, .95))

    def tap(self) -> None:
        self.mood = max(-100, self.mood - 12)
        self.mischief = min(100, self.mischief + 2)


class Brain:
    def __init__(self, seed: int = 20261025, personality: str = 'scholar') -> None:
        self.personality = personality
        self.rng = random.Random(seed)
        self.remaining = 0.0
        # Civic simulation is a voluntary, in-app preference from v0.19.
        # No changes to the default, historically seeded brain.
        self.civic_bias = (0, 0, 0, 0, 0, 0)

    def set_civic_bias(self, bias: tuple[int, ...] | None) -> None:
        if bias is None:
            self.civic_bias = (0, 0, 0, 0, 0, 0)
        elif (type(bias) is tuple and len(bias) == 6 and
              all(type(v) is int and 0 <= v <= 30 for v in bias)):
            self.civic_bias = bias
        else:
            raise ValueError('invalid local civic animation weights')

    def next(self, state: PetState, dt: float) -> str | None:
        """Return an action change or None; action duration is simulated seconds."""
        if dt < 0:
            raise ValueError('negative time')
        self.remaining -= dt
        if self.remaining > 0:
            return None
        if state.energy < 20:
            pick = 'sleep'
        else:
            actions = ['idle', 'walk', 'blink', 'sleep', 'turn']
            weights = [42, 34 + state.curiosity / 8, 16, 2 + (100 - state.energy) / 7, 10]
            if self.personality == 'sleepy':
                weights[0] += 17; weights[3] += 32; weights[1] *= .55
            elif self.personality == 'trickster':
                weights[1] += 20; weights[4] += 15; weights[3] *= .4
            elif self.personality == 'inventor':
                weights[1] += 8; weights[2] += 20; weights[4] += 6
            elif self.personality == 'captain':
                weights[1] += 18; weights[4] += 18; weights[3] *= .55
            elif self.personality == 'shy':
                weights[0] += 34; weights[2] += 12; weights[1] *= .65
            else:  # scholar: prefers pondering and blinking
                weights[0] += 12; weights[2] += 16
            if state.mode == 'MONKEY':
                actions.append('run')
                run_bias = {'trickster': 35, 'sleepy': 8, 'inventor': 16,
                            'captain': 25, 'shy': 5, 'scholar': 18}
                weights.append(run_bias.get(self.personality, 18) + state.mischief / 5)
            # Existing order: idle,walk,blink,sleep,turn,run. The sixth
            # weight only applies in MONKEY mode; QUIET never gains running.
            weights = [w + self.civic_bias[i] for i, w in enumerate(weights)]
            pick = self.rng.choices(actions, weights=weights, k=1)[0]
        state.action = pick
        self.remaining = self.rng.uniform(2.0, 5.0) if pick in ('walk', 'run', 'idle') else self.rng.uniform(0.8, 2.0)
        if pick == 'sleep':
            self.remaining = self.rng.uniform(4.0, 7.0)
        return pick

    def reset(self) -> None:
        self.remaining = 0.0
