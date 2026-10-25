"""Offline packaging previews of OUR OWN assets; no screenshot/grab calls."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from core.events import SCRIPTS
from core.animation import load_manifest

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/monkey'
DOC=ROOT/'docs'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

def font(size):
    try:return ImageFont.truetype(FONT,size)
    except OSError:return ImageFont.load_default()


def character(specs,name,i=0,size=140):
    if name not in specs:name='idle'
    path=ART/specs[name].frames[i%len(specs[name].frames)]
    return Image.open(path).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)


def main():
    specs=load_manifest(ART/'manifest.json')
    actions=['idle','blink','walk','run','turn','sleep','wake','eat_banana','slip','fall','get_up','angry','dragged']
    sheet=Image.new('RGB',(4*260,4*245),(245,241,231))
    pen=ImageDraw.Draw(sheet)
    for i,name in enumerate(actions):
        x=(i%4)*260;y=(i//4)*245
        pen.rounded_rectangle((x+13,y+10,x+245,y+231),radius=22,fill=(255,252,245),outline=(230,216,194),width=2)
        p=character(specs,name, min(1,len(specs[name].frames)-1),182)
        sheet.paste(p,(x+40,y+10),p)
        pen.text((x+80,y+191),name,fill=(83,47,32),font=font(21))
    sheet.save(DOC/'P03_P12_13_actions.png')
    frames=[]
    beat_list=SCRIPTS['banana']
    for b in beat_list:
        spec=specs.get(b.action,specs['idle'])
        num=max(2,int(b.seconds*8))
        for i in range(num):
            canvas=Image.new('RGBA',(440,290),(240,232,210,255))
            d=ImageDraw.Draw(canvas)
            d.rounded_rectangle((17,10,423,68),radius=17,fill=(255,245,206),outline=(91,63,44),width=2)
            d.text((29,18),b.line,fill=(91,47,34),font=font(21))
            char=character(specs,b.action,i,198)
            canvas.alpha_composite(char,(90,82))
            if b.prop in ('banana','peel'):
                d.arc((304,193,394,274),-60,150,fill=(242,188,34),width=13)
            if b.prop=='sign':
                d.rounded_rectangle((302,141,416,203),radius=8,fill=(248,227,189),outline=(88,54,36),width=4)
                d.text((320,155),'甩锅',fill=(120,43,24),font=font(21))
            frames.append(canvas.convert('RGB'))
    frames[0].save(DOC/'P03_P12_banana_demo.gif',save_all=True,append_images=frames[1:],duration=125,loop=0,optimize=True)

if __name__ == '__main__':main()
