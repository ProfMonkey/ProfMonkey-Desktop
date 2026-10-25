"""Reproducible original placeholder action frames for the P02 animation demo.

Developer-only generator: uses original P01 SVG, CairoSVG and Pillow. Runtime
needs ONLY PySide6; generated PNGs are committed to the repo. Frames share a
fixed 256x256 RGBA canvas and the same bottom-center anchor.

Usage: python tools/generate_p02_frames.py
"""
from __future__ import annotations

import io
import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets" / "monkey"
OUT = ART / "animations"
SOURCE = (ART / "profmonkey_idle.svg").read_text(encoding="utf-8")
OUT.mkdir(parents=True, exist_ok=True)


def svg_pose(*, eyes="open", bob=0.0, stride=0.0, sway=0.0, z=0, mouth="smile") -> Image.Image:
    s = SOURCE
    # Single group keeps same canvas, same contact point; no frame is cropped.
    s = s.replace(
        '<g stroke="#3a211c" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round">',
        f'<g transform="translate(0 {bob:.2f}) rotate({sway:.2f} 127 215)" stroke="#3a211c" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round">',
        1,
    )
    for cx, offset in ((96, stride), (158, -stride)):
        s = s.replace(
            f'<ellipse cx="{cx}" cy="236" rx="24" ry="12" fill="#744626"/>',
            f'<ellipse cx="{cx + offset:.2f}" cy="{236-abs(offset)*0.29:.2f}" rx="24" ry="12" fill="#744626"/>',
            1,
        )
    for origin, base, change in (("74 203", 18, stride * 2.2), ("181 203", -18, -stride * 2.2)):
        s = s.replace(f'rotate({base} {origin})', f'rotate({base + change:.2f} {origin})', 1)
    open_eyes = '''<ellipse cx="110" cy="110" rx="5.7" ry="8.7" fill="#2e2624" stroke="none"/>
    <ellipse cx="145" cy="110" rx="5.7" ry="8.7" fill="#2e2624" stroke="none"/>
    <circle cx="112" cy="107" r="2" fill="#fffdf1" stroke="none"/>
    <circle cx="147" cy="107" r="2" fill="#fffdf1" stroke="none"/>'''
    if eyes == "closed":
        new_eyes = '''<path d="M102 110 Q110 117 118 109 M137 109 Q145 117 153 110" stroke="#51372c" stroke-width="4" fill="none"/>'''
    elif eyes == "half":
        new_eyes = '''<ellipse cx="110" cy="111" rx="5.7" ry="3.5" fill="#2e2624" stroke="none"/>
    <ellipse cx="145" cy="111" rx="5.7" ry="3.5" fill="#2e2624" stroke="none"/>'''
    else:
        new_eyes = open_eyes
    assert open_eyes in s, "Base source eye design changed"
    s = s.replace(open_eyes, new_eyes, 1)
    if mouth == "o":
        s = s.replace('<path d="M108 145 Q128 160 148 143" fill="none" stroke="#673b33" stroke-width="4"/>',
                      '<ellipse cx="127" cy="149" rx="6" ry="7" fill="#673b33" stroke="none"/>', 1)
    if z:
        bubble = f'<text x="192" y="65" font-family="DejaVu Sans,Arial,sans-serif" font-size="{20 + z}" font-weight="bold" fill="#7a4f9d" stroke="none" opacity=".75">Zz</text>'
        s = s.replace('</svg>', bubble + '\n</svg>')
    raw = cairosvg.svg2png(bytestring=s.encode("utf-8"), output_width=256, output_height=256)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def save(name: str, images: list[Image.Image]) -> None:
    target = OUT / name
    target.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(images):
        assert image.size == (256, 256)
        image.save(target / f"{index:02}.png", optimize=True)


def squash(src: Image.Image, x_scale: float) -> Image.Image:
    # Center on same base anchor x=128, feet just above y=244.
    w = max(6, round(256 * x_scale))
    resized = src.resize((w, 256), Image.Resampling.LANCZOS)
    dest = Image.new("RGBA", (256, 256))
    dest.alpha_composite(resized, ((256 - w) // 2, 0))
    return dest


def rotated(src: Image.Image, degrees: float) -> Image.Image:
    # Tilt body without clipping using a shorter silhouette and stable ground.
    if abs(degrees) < 0.01:
        return src.copy()
    bbox = src.getbbox()
    crop = src.crop(bbox)
    scale = 0.83
    crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
    spin = crop.rotate(degrees, Image.Resampling.BICUBIC, expand=True)
    # Anchor rotated shape to same logical floor and character center.
    dest = Image.new("RGBA", (256, 256))
    x = (256 - spin.width) // 2
    y = min(247 - spin.height, 256 - spin.height)
    dest.alpha_composite(spin, (x, y))
    return dest


def generate() -> None:
    idle = [svg_pose(bob=b, sway=s) for b, s in [(0, 0), (-1, -0.8), (0, 0), (1, 0.8)]]
    blink = [svg_pose(eyes="half"), svg_pose(eyes="closed"), svg_pose(eyes="closed"), svg_pose(eyes="half")]
    walk = [svg_pose(bob=(-2 if i % 2 == 0 else 0), stride=math.sin(i * math.pi / 4) * 9, sway=math.sin(i * math.pi / 4) * 1.4) for i in range(8)]
    turn = [squash(svg_pose(), s) for s in [1.0, .82, .54, .20, .54, .82, 1.0]]
    sleep = [svg_pose(eyes="closed", bob=b, sway=1.2, z=z, mouth="o") for b, z in [(2, 0), (3, 2), (3, 5), (2, 3)]]
    wake = [svg_pose(eyes=e, bob=b, mouth=m) for e, b, m in [
        ("closed", 2, "o"), ("half", 1, "o"), ("half", 0, "smile"), ("open", -3, "o"), ("open", 0, "smile")
    ]]
    falling_angles = [0, -12, -25, -44, -61, -72]
    fall = [rotated(svg_pose(eyes="open", mouth="o"), ang) for ang in falling_angles]
    get_up = [rotated(svg_pose(eyes="half"), ang) for ang in [-72, -52, -30, -12, 5, 0]]
    for name, imgs in (
        ("idle", idle), ("blink", blink), ("walk", walk), ("turn", turn),
        ("sleep", sleep), ("wake", wake), ("fall", fall), ("get_up", get_up),
    ):
        save(name, imgs)
        print(f"{name}: {len(imgs)} generated PNG frames")
    # One visual preview artifact does NOT include the user's screen.
    from PIL import ImageDraw
    strip = Image.new("RGB", (256 * 8, 300), (239, 236, 224))
    draw = ImageDraw.Draw(strip)
    for col, (name, imgs) in enumerate((("idle", idle), ("blink", blink), ("walk", walk), ("turn", turn),
                                       ("sleep", sleep), ("wake", wake), ("fall", fall), ("get_up", get_up))):
        strip.paste(imgs[len(imgs) // 2], (col * 256, 0), imgs[len(imgs) // 2])
        draw.text((col * 256 + 90, 264), name, fill=(52, 32, 27))
    preview = ROOT / "docs" / "P02_animation_contact_sheet.png"
    strip.save(preview)
    print("Contact sheet:", preview)


if __name__ == "__main__":
    generate()
