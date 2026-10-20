#!/usr/bin/env python3
"""Rebuild the favicon set from assets/logo.png (crops the circular mark, sets it on a white rounded tile).
Writes favicon.ico, favicon-32.png, favicon-192.png, apple-touch-icon.png to the repo root. The 32 px icon is also embedded in index.html as a data URI."""
from PIL import Image, ImageDraw
import numpy as np
im = Image.open('assets/logo.png').convert('RGB'); ink = np.array(im).sum(axis=2) < 700; cols = ink.any(axis=0)
x = int(np.argmax(cols)); gap = 0
while x < len(cols):
    gap = gap + 1 if not cols[x] else 0
    if gap >= 8: break
    x += 1
icon = im.crop((0, 0, x - gap + 1, im.height)).convert('RGBA'); S = 1024
tile = Image.new('RGBA', (S, S), (0, 0, 0, 0)); ImageDraw.Draw(tile).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * .22), fill=(255, 255, 255, 255))
side = int(S * .78); ic = icon.resize((side, int(side * icon.height / icon.width)), Image.LANCZOS); tile.paste(ic, ((S - ic.width) // 2, (S - ic.height) // 2), ic)
for name, px in (('favicon-32.png', 32), ('favicon-192.png', 192)): tile.resize((px, px), Image.LANCZOS).save(name, optimize=True)
t = tile.resize((180, 180), Image.LANCZOS); bg = Image.new('RGB', (180, 180), 'white'); bg.paste(t, mask=t.split()[3]); bg.save('apple-touch-icon.png', optimize=True)
tile.resize((48, 48), Image.LANCZOS).save('favicon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
print('favicon files written')
