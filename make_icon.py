#!/usr/bin/env python3
"""Regenerate the app icon (build/icon.ico + build/icon.png). Needs Pillow.
   A gold crafting hammer on the app's dark/gold theme. Run: python3 make_icon.py"""
from PIL import Image, ImageDraw
import os

S = 1024
os.makedirs("build", exist_ok=True)

# background: rounded square, vertical dark gradient + gold border
grad = Image.new("RGB", (1, S))
for y in range(S):
    t = y / S
    r = int(0x2a + (0x0b - 0x2a) * t)
    g = int(0x1d + (0x08 - 0x1d) * t)
    b = int(0x0c + (0x05 - 0x0c) * t)
    grad.putpixel((0, y), (r, g, b))
grad = grad.resize((S, S))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([34, 34, S - 34, S - 34], radius=200, fill=255)
bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
bg.paste(grad, (0, 0), mask)
ImageDraw.Draw(bg).rounded_rectangle([34, 34, S - 34, S - 34], radius=200, outline=(201, 162, 75, 255), width=16)

# hammer on its own layer, then rotate
GOLD, GOLD_D, HL = (230, 200, 120, 255), (150, 112, 46, 255), (255, 242, 205, 255)
HANDLE, HANDLE_HL = (120, 84, 40, 255), (160, 116, 60, 255)
ham = Image.new("RGBA", (S, S), (0, 0, 0, 0))
hd = ImageDraw.Draw(ham)
cx = 512
hd.rounded_rectangle([cx - 30, 380, cx + 30, 840], radius=30, fill=HANDLE)
hd.rounded_rectangle([cx - 30, 380, cx - 8, 840], radius=18, fill=HANDLE_HL)
hd.rounded_rectangle([cx - 225, 250, cx + 225, 405], radius=46, fill=GOLD)
hd.rounded_rectangle([cx - 225, 360, cx + 225, 405], radius=46, fill=GOLD_D)
hd.rounded_rectangle([cx - 205, 268, cx + 205, 312], radius=22, fill=HL)
ham = ham.rotate(-26, resample=Image.BICUBIC, center=(cx, 430))

out = Image.alpha_composite(bg, ham)
od = ImageDraw.Draw(out)
for sx, sy, r in [(735, 300, 20), (782, 358, 11), (712, 392, 9)]:
    od.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 236, 175, 255))

out.save("build/icon.png")
out.save("build/icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("wrote build/icon.png and build/icon.ico")
