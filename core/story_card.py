"""Render shareable story cards from bundled monkey art only; never screen capture."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from core.profiles import clean_profiles, PERSONALITIES

STORIES = {
    'banana': ('香蕉事故调查报告', '教授吃掉证据，摔倒后宣布：都是你的问题！'),
    'blackboard': ('猴学委员会·学术现场', '当 1+1=3 被质疑，教授决定把答案改成：猴。'),
    'mirror': ('镜像事故', '镜子里的猴子拒绝承认自己是副本。'),
    'keyboard': ('键盘暴走', '键盘坏了没关系，香蕉依然可以继续敲。'),
    'edge': ('边缘坠落事件', '教授从边缘滑落，随后坚称这是一次重力实验。'),
    'meeting': ('猴学委员会会议纪要', '证据已被吃掉，本次会议仍然全票通过。'),
    'banana_duel': ('香蕉争夺战', '规则在开赛后临时修改，输家表示不服。'),
}


def _font(size: int):
    for name in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_story_card(idle: Path, profiles: list[dict], count: int,
                      story_key: str, destination: Path,
                      relationship_line: str = '') -> tuple[int, int]:
    if not 1 <= count <= 6:
        raise ValueError('story card supports 1 to 6 monkeys')
    if story_key not in STORIES:
        raise ValueError('unknown story')
    profiles = clean_profiles(profiles)
    W, H = 1200, 800
    image = Image.new('RGB', (W, H), '#151824')
    draw = ImageDraw.Draw(image)
    for y in range(H):
        t = y / H
        draw.line((0, y, W, y), fill=(int(22+14*t), int(25+8*t), int(38+12*t)))
    draw.rounded_rectangle((24, 24, W-24, H-24), radius=30, outline='#92724a', width=3)
    draw.text((68, 58), 'ProfMonkey  /  猴山故事档案', font=_font(26), fill='#c6b7a3')
    title, summary = STORIES[story_key]
    draw.text((66, 108), title, font=_font(43), fill='#f6ca7c')
    draw.text((68, 174), summary, font=_font(22), fill='#e7dfd1')
    base = Image.open(idle).convert('RGBA')
    cols = min(count, 3)
    rows = (count + cols - 1) // cols
    card_w = 320 if count <= 3 else 340
    card_h = 210 if rows == 2 else 270
    gap = 16
    start_y = 240
    accents = {'scholar':'#eac373','trickster':'#f8a391','sleepy':'#9cbde2'}
    poses = {'scholar':'idle','trickster':'angry','sleepy':'sleep'}
    for i in range(count):
        col, row = i % cols, i // cols
        row_count = min(cols, count - row*cols)
        row_start_x = (W - (row_count*card_w + (row_count-1)*gap))//2
        x = row_start_x + col*(card_w+gap)
        y = start_y + row*(card_h+gap)
        draw.rounded_rectangle((x, y, x+card_w, y+card_h), radius=20, fill='#292d40', outline='#5a5364', width=2)
        frame = idle.parent/'animations'/poses[profiles[i]['personality']]/f'{i%4:02d}.png'
        art = Image.open(frame).convert('RGBA') if frame.is_file() else base.copy()
        art.thumbnail((150, 150), Image.Resampling.LANCZOS)
        image.paste(art, (x+18, y+14), art)
        draw.ellipse((x+card_w-34, y+18, x+card_w-16, y+36), fill=accents[profiles[i]['personality']])
        draw.text((x+174, y+35), profiles[i]['name'], font=_font(22), fill='#ffe6bc')
        draw.text((x+174, y+72), PERSONALITIES[profiles[i]['personality']], font=_font(16), fill='#bcb7ca')
        draw.text((x+174, y+108), f'NO.{i+1:02d}', font=_font(15), fill='#8e91a7')
    footer = relationship_line.strip()[:70] if relationship_line else '纯本地生成 · 只包含猴子素材，不包含桌面截图'
    draw.text((68, H-82), footer, font=_font(18), fill='#d6c9b7')
    draw.text((68, H-51), f'{datetime.now().strftime("%Y-%m-%d %H:%M")}   ·   宇宙很大，猴子很忙。',
              font=_font(15), fill='#a8a8bb')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format='PNG')
    return image.size
