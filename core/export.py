"""Export only packaged sprite frames (never screenshots of the desktop)."""
from pathlib import Path
from PIL import Image
from core.animation import load_manifest
from core.character_raster import raster_mascot


def export_action_gif(manifest: Path, action: str, destination: Path, size: int = 160, *, personality: str = 'scholar') -> int:
    specs = load_manifest(manifest)
    if action not in specs:
        raise ValueError('unknown animation')
    spec = specs[action]
    frames = []
    for idx, _rel in enumerate(spec.frames):
        frame = raster_mascot(manifest.parent, personality, action,
                              idx, len(spec.frames))
        frame.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(frame, ((size - frame.width) // 2, size - frame.height))
        # GIF palette transparency is approximate: enforce a single transparent key.
        pal = canvas.convert('P', palette=Image.Palette.ADAPTIVE, colors=255)
        mask = canvas.getchannel('A').point(lambda a: 255 if a < 40 else 0)
        pal.paste(255, mask=mask)
        pal.putpalette(pal.getpalette()[:255 * 3] + [0, 0, 0])
        pal.info['transparency'] = 255
        frames.append(pal)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(destination, save_all=True, append_images=frames[1:],
                   duration=max(50, round(1000 / spec.fps)), loop=0,
                   transparency=255, disposal=2, optimize=False)
    return len(frames)


def export_story_gif(manifest: Path, script_name: str, destination: Path, *, fps: int = 8,
                     personality: str = 'scholar') -> int:
    """Render story cards using only bundled sprites + in-app props.

    Privacy guarantee by construction: accepts a manifest and script key, never
    a screen region, window title, desktop pixels, or arbitrary captured image.
    """
    from PIL import ImageDraw, ImageFont
    from core.events import SCRIPTS
    if script_name not in SCRIPTS:
        raise ValueError('unknown story')
    specs = load_manifest(manifest)
    frames=[]
    def select_font(size):
        # System fonts are optional; never distribute unlicensed font binaries.
        candidates=(
            r'C:\Windows\Fonts\msyh.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        )
        for name in candidates:
            try:
                return ImageFont.truetype(name,size)
            except OSError:
                pass
        return ImageFont.load_default()
    chinese = select_font(19)
    for beat in SCRIPTS[script_name]:
        spec = specs.get(beat.action, specs['idle'])
        n=max(1,int(beat.seconds*fps))
        for k in range(n):
            bg=Image.new('RGB',(420,270),'#F1EDE4')
            d=ImageDraw.Draw(bg)
            d.rounded_rectangle((12,10,408,63),radius=13,fill='#FFF2CD',outline='#684A39',width=2)
            d.text((24,22),beat.line,fill='#53382A',font=chinese)
            sprite=raster_mascot(manifest.parent, personality, spec.name,
                                  k % len(spec.frames), len(spec.frames))
            sprite.thumbnail((190,190),Image.Resampling.LANCZOS)
            bg.paste(sprite,(87,73),sprite)
            if beat.prop in ('banana','peel'):
                d.arc((278,172,382,247),-40,158,fill='#F1BB34',width=12)
            elif beat.prop=='sign':
                d.rounded_rectangle((280,151,401,209),radius=5,fill='#FAE0BB',outline='#57382C',width=3)
                d.text((302,165),'甩锅',fill='#9E4035',font=chinese)
            elif beat.prop in ('board','keyboard','keyboard_broken'):
                d.rounded_rectangle((282,154,400,206),radius=5,fill='#407360' if beat.prop=='board' else '#A5CCD3',outline='#57382C',width=3)
                d.text((291,164),'1+1=猴' if beat.line=='1 + 1 = 猴' else '1+1=3' if beat.prop=='board' else '⌨',fill='white',font=chinese)
            elif beat.prop.startswith('mirror'):
                d.ellipse((288,153,373,240),fill='#ACDFEA',outline='#57382C',width=4)
                if beat.prop=='mirror_twins':
                    mini=sprite.resize((93,93),Image.Resampling.LANCZOS)
                    bg.paste(mini,(277,160),mini)
            frames.append(bg)
    destination.parent.mkdir(parents=True,exist_ok=True)
    frames[0].save(destination,save_all=True,append_images=frames[1:],
                   duration=round(1000/fps),loop=0,optimize=True)
    return len(frames)
