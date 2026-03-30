import sys
from PIL import Image, ImageDraw

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/test_box.png"

img = Image.open(img_path).convert("RGB")
draw = ImageDraw.Draw(img)

# Let's draw a red box from 100, 100 to 1350, 800
draw.rectangle([100, 100, 1350, 800], outline="red", width=10)
# Let's draw another one for the exact text areas:
draw.rectangle([250, 70, 950, 150], outline="green", width=10) # BTC·ETH ETF 유출입 ?
draw.rectangle([500, 150, 950, 200], outline="blue", width=10) # (ETF 데이터는 마지막 거래일 기준) ?

img.save(out_path)
