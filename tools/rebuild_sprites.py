"""Rebuild 512x512 spritesheets from the bundled original transparent 4x4 PNG files.

Usage (run from project folder):
    python tools/rebuild_sprites.py
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'assets'
manifest=json.loads((DIR/'characters'/'manifest.json').read_text(encoding='utf-8'))

for name, info in manifest.items():
    image=Image.open(DIR/'original_sheets'/info['source']).convert('RGBA')
    ex=[round(image.width*i/4) for i in range(5)]
    ey=[round(image.height*i/4) for i in range(5)]
    frames=[]; boxes=[]
    for r in range(4):
        for c in range(4):
            cell=image.crop((ex[c],ey[r],ex[c+1],ey[r+1]))
            box=cell.getchannel('A').point(lambda a: 255 if a>20 else 0).getbbox()
            if not box: raise ValueError(f'Empty frame: {name} ({r},{c})')
            frames.append(cell);boxes.append(box)
    hmax=max(y1-y0 for x0,y0,x1,y1 in boxes)
    wmax=max(x1-x0 for x0,y0,x1,y1 in boxes)
    scale=min(98/hmax,108/wmax)
    out=Image.new('RGBA',(512,512))
    for k,(im,box) in enumerate(zip(frames,boxes)):
        sprite=im.crop(box)
        w=max(1,round(sprite.width*scale));h=max(1,round(sprite.height*scale))
        sprite=sprite.resize((w,h),Image.Resampling.NEAREST)
        sprite.putalpha(sprite.getchannel('A').point(lambda a: 0 if a<20 else a))
        out.alpha_composite(sprite,((k%4)*128+(128-w)//2,(k//4)*128+118-h))
    out.save(DIR/'characters'/f'{name}.png')
    print(f'Rebuilt {name}.png')
