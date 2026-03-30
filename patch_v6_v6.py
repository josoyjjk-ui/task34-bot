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
empty_patch = img.crop((850, 300, 1300, 600)) # 450x300

# 1. Patch Title "BTC·ETF ETF 유출입"
# Based on earlier: Title is [150, 120, 700, 195]
patch1 = empty_patch.resize((650, 80))
img.paste(patch1, (160, 115))

f_title = load_font(FONT_KO_BOLD, 75, 3)
draw.text((180, 110), "BTC ETH 유출입", font=f_title, fill=(240, 240, 200))

# 2. Patch ETH Section
# Based on earlier: "ETH (+52M)" is [200, 390, 550, 450]
# ETH details are [110, 450, 700, 510]
# So patch [100, 390, 750, 530]
patch2 = empty_patch.resize((680, 150))
img.paste(patch2, (100, 390))

f_eth_header = load_font(FONT_CHALK_BOLD, 65, 1)
draw.text((250, 390), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

f_eth_text = load_font(FONT_KO_BOLD, 50, 3)
draw.text((100, 460), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((320, 460), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((580, 460), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

patch3 = empty_patch.resize((680, 60))
img.paste(patch3, (100, 515)) # extra space for the second line
draw.text((320, 510), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((580, 510), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

img.save(out_path)
print(f"Saved {out_path}")
