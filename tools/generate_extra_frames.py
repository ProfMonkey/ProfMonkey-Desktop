"""Generate original companion P03+ animation frames from our existing artwork.
Runtime never needs Pillow; generated images are bundled.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/monkey'
MANIFEST = ART / 'manifest.json'
base = Image.open(ART / 'animations/idle/00.png').convert('RGBA')


def draw_pose(name, index):
    img = base.copy()
    d = ImageDraw.Draw(img)
    if name == 'eat_banana':
        # A clear bright banana silhouette next to the mouth, animated by angle.
        p = index % 4
        x, y = 175 - 8 * p, 155 - 7 * p
        d.arc((x-36, y-38, x+26, y+35), 25, 155, fill=(79, 48, 18, 255), width=17)
        d.arc((x-36, y-38, x+26, y+35), 25, 155, fill=(252, 212, 54, 255), width=12)
        d.ellipse((x+14, y-30, x+21, y-23), fill=(76, 52, 31, 255))
    elif name == 'angry':
        # Raised eyebrows and stress marks, no borrowed character art.
        d.line((91,83,115,89), fill=(75, 34, 26,255), width=6)
        d.line((138,89,162,83), fill=(75, 34, 26,255), width=6)
        d.polygon([(191,40),(201,62),(210,42)], fill=(230, 80, 76, 230))
        if index % 2:
            d.ellipse((75,160,94,174), fill=(226, 110, 86, 160))
    elif name == 'dragged':
        d.ellipse((104,141,150,153), fill=(88, 40, 30, 255))
        for x in (88,165):
            d.line((x,185,x,210), fill=(90, 40, 30, 255), width=5)
    elif name == 'slip':
        # Rotate existing sprite around center, same fixed bottom anchor.
        a = [-8, -21, -40, -60][index % 4]
        box = base.getbbox()
        sub = base.crop(box)
        sub = sub.resize((int(sub.width*.80), int(sub.height*.80)))
        sub = sub.rotate(a, expand=True)
        img = Image.new('RGBA',(256,256),(0,0,0,0))
        img.alpha_composite(sub, ((256-sub.width)//2, 247-sub.height))
    elif name == 'run':
        source = Image.open(ART/f'animations/walk/{(index*2)%8:02}.png').convert('RGBA')
        img = source
        d = ImageDraw.Draw(img)
        d.line([(20,185),(45,185)], fill=(151, 120, 78, 200), width=4)
        d.line([(12,199),(39,199)], fill=(151, 120, 78, 180), width=3)
    return img


def main():
    raw = json.loads(MANIFEST.read_text(encoding='utf-8'))
    data = {
        'eat_banana': (6, 7.0, False, 5, False, 'idle'),
        'slip': (4, 9.0, False, 8, False, 'fall'),
        'angry': (4, 5.0, False, 5, False, 'idle'),
        'dragged': (2, 5.0, True, 9, True, 'idle'),
        'run': (6, 12.0, True, 1, True, 'idle'),
    }
    for name, (count, fps, loop, priority, interruptible, next_action) in data.items():
        folder = ART/'animations'/name
        folder.mkdir(parents=True, exist_ok=True)
        frames=[]
        for i in range(count):
            path = folder/f'{i:02}.png'
            draw_pose(name, i).save(path, optimize=True)
            frames.append(f'animations/{name}/{i:02}.png')
        raw['states'][name] = {
            'implemented': True, 'frames': frames, 'fps': fps, 'loop': loop,
            'priority': priority, 'interruptible': interruptible,
            'next_action': next_action,
            'hitbox': 'per-frame alpha', 'anchor_normalized': [0.5, 0.96]
        }
    raw['animation_phase'] = 'P03-P12 candidate actions; Windows acceptance pending'
    MANIFEST.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
