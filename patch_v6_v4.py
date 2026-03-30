import sys
from PIL import Image, ImageDraw, ImageFont

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_final.png"

img = Image.open(img_path).convert("RGB")
draw = ImageDraw.Draw(img)

def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()

FONT_KO_BOLD = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FONT_CHALK_BOLD = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
FONT_CHALK_REGULAR = "/System/Library/Fonts/Supplemental/Chalkboard.ttc"

# Let's get the background color directly from the image at a known empty spot (e.g., x=100, y=700)
bg_color = img.getpixel((100, 700))

# 1. Patch Title "BTC·ETF ETF 유출입" -> "BTC ETH 유출입"
# The title is at [200, 55, 710, 120]
draw.rectangle([200, 45, 750, 130], fill=bg_color)
f_title = load_font(FONT_KO_BOLD, 65, 3)
draw.text((250, 50), "BTC ETH 유출입", font=f_title, fill=(240, 240, 200))

# 2. Patch ETH Section
# "ETH (+52M)" is at [235, 370, 560, 430]
# "Total +52M 블랙록 +32M 피델리티 +15M" is at [115, 440, 680, 490]
draw.rectangle([100, 360, 750, 550], fill=bg_color)

f_eth_header = load_font(FONT_CHALK_BOLD, 55, 1)
draw.text((320, 370), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

f_eth_text = load_font(FONT_KO_BOLD, 45, 3)
draw.text((120, 440), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((360, 440), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((640, 440), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

draw.text((360, 495), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((640, 495), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

# We also need to fix BTC values if needed. The instruction says: "ETF(BTC/ETH), OI(BTC/ETH 24h·72h), DAT(BTC/ETH 24h·72h), 코인베이스 프리미엄(24h·72h)".
# The image already has:
# BTC (+199M) 블랙록 +139M 피델리티 +64M 비트와이즈 +2M 반에크 -6M (Which perfectly matches today's data!)
# OI: BTC 24h +3.5%, ETH 24h +2.1%, BTC 72h +5.1%, ETH 72h +3.8%
# DAT: 24h -1.2%, 72h +0.8%
# CB Premium: 24h +2.9%, 72h -0.5%
# Those can remain as they are, as they are part of today's snapshot that was already generated except for the ETH data which was incomplete.

img.save(out_path)
print(f"Saved {out_path}")
