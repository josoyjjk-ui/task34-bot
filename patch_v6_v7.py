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

# Crop a TRULY empty piece of the chalkboard
empty_patch = img.crop((850, 200, 1300, 400)) # 450x200

# 1. Patch Title "BTC·ETF ETF 유출입"
# Based on Y: 105 -> [160, 60, 750, 150]
patch1 = empty_patch.resize((650, 90))
img.paste(patch1, (160, 60))

f_title = load_font(FONT_KO_BOLD, 75, 3)
draw.text((250, 70), "BTC ETH 유출입", font=f_title, fill=(240, 240, 200))

# 2. Patch ETH Section
# "ETH (+52M)" Y: 430 -> y=390 to 460
# "Total..." Y: 500 -> y=470 to 530
# So patch [100, 400, 800, 580]
patch2 = empty_patch.resize((700, 180))
img.paste(patch2, (100, 400))

f_eth_header = load_font(FONT_CHALK_BOLD, 65, 1)
draw.text((320, 400), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

f_eth_text = load_font(FONT_KO_BOLD, 50, 3)
draw.text((100, 480), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((320, 480), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((600, 480), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

patch3 = empty_patch.resize((700, 70))
img.paste(patch3, (100, 540)) # extra space for the second line
draw.text((320, 540), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((600, 540), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

img.save(out_path)
print(f"Saved {out_path}")
