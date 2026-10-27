"""Deterministic v0.20 art director for six ORIGINAL balanced monkey mascots.

This is transparent 256x256 Qt-safe SVG; every role has its own vector drawing,
outfit, accessory, fur colors and silhouette. No AI-poster raster baked into
sprites, no dependence on missing v0.10 frames, and no network access.
Source SVGs are intentionally editable and retained alongside game code.

Pose replacement changes only trusted, bundled markup from six fixed paths.
The idle animation still uses the established 13 state manifest timings.
"""
from __future__ import annotations

from functools import lru_cache
from math import sin, pi
from pathlib import Path

CHARACTERS = ('scholar', 'trickster', 'sleepy', 'inventor', 'captain', 'shy')
SUPPORTED_ACTIONS = frozenset((
    'idle','blink','walk','turn','sleep','wake','fall','get_up',
    'eat_banana','slip','angry','dragged','run'
))
FOLDER = 'characters_v020'


def mascot_path(asset_root: Path, personality: str) -> Path:
    """asset_root is `assets/monkey`, not user-controlled filesystem input."""
    if personality not in CHARACTERS or type(personality) is not str:
        raise ValueError('unknown mascot personality')
    return Path(asset_root).parent / FOLDER / f'{personality}.svg'


@lru_cache(maxsize=12)
def _source(file: str) -> str:
    data = Path(file).read_text(encoding='utf-8')
    for marker in (
        'viewBox="0 0 256 256"', 'id="pose" transform="translate(0 0)"',
        'id="eyes-open" opacity="1"', 'id="eyes-closed" opacity="0"',
        'id="mouth-smile" opacity="1"', 'id="mouth-open" opacity="0"',
        'id="prop-banana" opacity="0"',
        'id="left-leg" transform="translate(0 0)"',
        'id="right-leg" transform="translate(0 0)"',
        'id="left-arm" transform="translate(0 0)"',
        'id="right-arm" transform="translate(0 0)"',
    ):
        if marker not in data:
            raise ValueError(f'invalid bundled monkey artwork: missing {marker}')
    # The required SVG namespace uses http://www.w3.org/2000/svg. Do not
    # block it; block only executable payloads and URL-linked image/font data.
    unsafe = ('<script', '<foreignobject', 'onload=', 'onerror=',
              'href="http:', 'href="https:', "href='http:",
              "href='https:", 'xlink:href=', 'url(http:', 'url(https:')
    if any(token in data.lower() for token in unsafe):
        raise ValueError('external SVG resources or scripts are not permitted')
    return data


def pose_svg(asset_root: Path, personality: str, action: str,
             frame: int = 0, frame_count: int = 1) -> bytes:
    """Return a full, self-contained SVG frame for exactly one monkey.

    Script-free SVG is rendered with QtSvg into memory; it does NOT contain
    text and isn't loaded from a website. Output is never attached to the
    real desktop, pointer, clipboard or accessibility APIs.
    """
    if action not in SUPPORTED_ACTIONS or type(action) is not str:
        raise ValueError('unknown animation action')
    if (type(frame) is not int or type(frame_count) is not int or
            frame < 0 or frame_count < 1 or frame >= frame_count or frame_count > 20):
        raise ValueError('invalid animation frame')
    raw = _source(str(mascot_path(asset_root, personality)))
    phase = 2*pi*frame / frame_count
    bob = 0
    lean = 0
    stride = 0
    arm = 0
    squash = 1
    closed = False
    open_mouth = False
    banana = action == 'eat_banana'
    if action == 'idle':
        bob = (-1, 0, 1, 0)[frame % 4]
    elif action == 'blink':
        closed = frame in (1, 2) or frame_count <= 2
    elif action == 'walk':
        bob = round(-2 * abs(sin(phase)))
        stride = round(5 * sin(phase))
        arm = -stride
        lean = round(1.5*sin(phase), 1)
    elif action == 'run':
        bob = round(-4 * abs(sin(phase)))
        stride = round(10 * sin(phase))
        arm = round(-1.4*stride)
        lean = round(3*sin(phase),1)
        open_mouth = True
    elif action == 'turn':
        sequence = (1, .75, .45, .18, .45, .75, 1)
        squash = sequence[min(6, frame * 7 // frame_count)]
    elif action == 'sleep':
        closed = True
        bob = (2,3,3,2)[frame % 4]
        lean = 3
    elif action == 'wake':
        closed = frame < max(1, frame_count//2)
        bob = 3 if closed else -2
        open_mouth = frame == frame_count - 2
    elif action == 'fall':
        open_mouth = True
        lean = -round(50 * frame/max(1,frame_count-1))
        bob = -4
    elif action == 'get_up':
        lean = -round(50 * (1-frame/max(1,frame_count-1)))
        closed = frame < frame_count//2
    elif action == 'slip':
        lean = -round(32*frame/max(1,frame_count-1))
        open_mouth = True
    elif action == 'angry':
        open_mouth = True
        lean = 2 if frame%2 else -2
    elif action == 'dragged':
        open_mouth = True
        bob = -3
        arm = -9 if frame%2 else 9
    if action == 'eat_banana':
        open_mouth = frame >= frame_count//2
        arm = -6
    base = f'translate(0 {bob}) rotate({lean} 128 192)'
    if action == 'turn':
        # Preserve the x=128 center without stretching overall widget/window.
        base += f' translate({128*(1-squash):.2f} 0) scale({squash:.3f} 1)'
    raw = raw.replace('id="pose" transform="translate(0 0)"',
                      f'id="pose" transform="{base}"', 1)
    if stride:
        raw = raw.replace('id="left-leg" transform="translate(0 0)"',
                          f'id="left-leg" transform="translate({stride} {-abs(stride)//3})"', 1)
        raw = raw.replace('id="right-leg" transform="translate(0 0)"',
                          f'id="right-leg" transform="translate({-stride} {-abs(stride)//3})"', 1)
    if arm:
        raw = raw.replace('id="left-arm" transform="translate(0 0)"',
                          f'id="left-arm" transform="rotate({arm} 87 151)"', 1)
        raw = raw.replace('id="right-arm" transform="translate(0 0)"',
                          f'id="right-arm" transform="rotate({-arm} 165 151)"', 1)
    if closed:
        raw = raw.replace('id="eyes-open" opacity="1"',
                          'id="eyes-open" opacity="0"', 1)
        raw = raw.replace('id="eyes-closed" opacity="0"',
                          'id="eyes-closed" opacity="1"', 1)
    if open_mouth:
        raw = raw.replace('id="mouth-smile" opacity="1"',
                          'id="mouth-smile" opacity="0"', 1)
        raw = raw.replace('id="mouth-open" opacity="0"',
                          'id="mouth-open" opacity="1"', 1)
    if banana:
        raw = raw.replace('id="prop-banana" opacity="0"',
                          'id="prop-banana" opacity="1"', 1)
    return raw.encode('utf-8')
