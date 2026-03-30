import sys
from PIL import Image, ImageDraw, ImageFont

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/grid.png"
img = Image.open(img_path).convert("RGB")
draw = ImageDraw.Draw(img)
def load_font(path, size, index=0):
    try: return ImageFont.truetype(path, size, index=index)
    except Exception: return ImageFont.load_default()
f = load_font("/System/Library/Fonts/AppleSDGothicNeo.ttc", 40, 3)

for y in range(0, 1500, 100):
    draw.line([(0, y), (2750, y)], fill="red", width=3)
    draw.text((10, y), str(y), font=f, fill="red")
    draw.text((1300, y), str(y), font=f, fill="red")

for x in range(0, 2750, 200):
    draw.line([(x, 0), (x, 1500)], fill="blue", width=3)
    draw.text((x, 10), str(x), font=f, fill="blue")

img.save(out_path)
