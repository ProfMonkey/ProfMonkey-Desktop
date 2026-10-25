"""Create a local, shareable group portrait ONLY from bundled monkey artwork.

Never capture the desktop, applications, mouse cursor, or anything on-screen.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from core.profiles import clean_profiles, PERSONALITIES


def _font(size: int):
    for name in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\simhei.ttf',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name,size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_colony_portrait(idle: Path, profiles: list[dict], count: int,
                            destination: Path) -> tuple[int,int]:
    """Generate a 1000x660 PNG, using only user-provided names and bundled image."""
    if not 1 <= count <= 6:
        raise ValueError('portrait supports 1 to 6 monkeys')
    base = Image.open(idle).convert('RGBA')
    profiles = clean_profiles(profiles)
    W,H = 1000, 660
    image = Image.new('RGB',(W,H),'#141822')
    draw = ImageDraw.Draw(image)
    for y in range(H):
        mix = y/H
        color = (int(20+14*mix),int(24+9*mix),int(34+14*mix))
        draw.line((0,y,W,y),fill=color)
    draw.rounded_rectangle((28,28,W-28,H-28),radius=26,outline='#846948',width=3)
    draw.text((65,49),'ProfMonkey  /  猴山研究院',font=_font(35),fill='#f7ca7d')
    draw.text((67,105),f'{count} 位教授 · 一份离线合照 · 宇宙很大，猴子很忙。',font=_font(19),fill='#beb8ae')
    cols = min(count,3)
    rows = (count + cols - 1)//cols
    card_w = 272
    card_h = 205 if rows == 2 else 375
    hgap = 18
    start_x = (W - (cols*card_w+(cols-1)*hgap))//2
    start_y = 160 if rows==2 else 176
    accents = {'scholar':'#eac373','trickster':'#f8a391','sleepy':'#9cbde2'}
    for i in range(count):
        col,row = i % cols, i//cols
        x = start_x+col*(card_w+hgap)
        y = start_y+row*(card_h+12)
        draw.rounded_rectangle((x,y,x+card_w,y+card_h),radius=20,fill='#242737',outline='#5e5150',width=2)
        # Portrait art stays entirely within the card, even with six characters.
        art_size = 157 if rows == 2 else 258
        variant = {'scholar':'idle','trickster':'angry','sleepy':'sleep'}[profiles[i]['personality']]
        pose = idle.parent / 'animations' / variant / f'{i%4:02d}.png'
        art=Image.open(pose).convert('RGBA') if pose.is_file() else base.copy()
        art.thumbnail((art_size,art_size),Image.Resampling.LANCZOS)
        image.paste(art,(x+(card_w-art.width)//2,y+4),art)
        bottom = y+card_h-76
        draw.rounded_rectangle((x+13,bottom,x+card_w-13,y+card_h-13),radius=11,fill='#333344')
        draw.ellipse((x+card_w-33,y+12,x+card_w-15,y+30),fill=accents[profiles[i]['personality']])
        draw.text((x+23,bottom+7),profiles[i]['name'],font=_font(21),fill='#ffe4b7')
        draw.text((x+23,bottom+37),f'NO.{i+1:02d}  /  {PERSONALITIES[profiles[i]["personality"]]}',
                  font=_font(13),fill='#b6acc3')
    draw.text((68,H-55),'只有猴子的原创素材；不会包含你的桌面或其他软件内容。',
              font=_font(15),fill='#9e9eaf')
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    image.save(destination,format='PNG')
    return image.size
