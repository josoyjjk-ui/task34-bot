import sys
from PIL import Image, ImageDraw, ImageFont

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_patched3.png"

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

# We will use solid colors that closely match the chalkboard to patch
# Or better, crop from an empty area: y=500 to 700 in the left panel is empty.
empty_patch = img.crop((100, 500, 800, 700)) # 700x200

# 1. Patch Title "BTC·ETF ETF 유출입"
# Bounding box: [200, 55, 710, 120] -> let's cover [200, 45, 750, 130]
patch_title = empty_patch.resize((550, 85))
img.paste(patch_title, (200, 45))
f_title = load_font(FONT_KO_BOLD, 65, 3)
draw.text((250, 50), "BTC ETH 유출입", font=f_title, fill=(240, 240, 200))

# 2. Patch ETH Section
# Bounding boxes:
# "ETH (+52M)" [235, 370, 560, 430]
# "Total +52M 블랙록 +32M 피델리티 +15M" [115, 440, 680, 490]
# Cover [100, 360, 750, 500]
patch_eth = empty_patch.resize((650, 140))
img.paste(patch_eth, (100, 360))

f_eth_header = load_font(FONT_CHALK_BOLD, 55, 1)
draw.text((320, 370), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

f_eth_text = load_font(FONT_KO_BOLD, 45, 3)
draw.text((120, 440), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((360, 440), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((640, 440), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

# Add the negative values on the next line (y=495)
# So we need to cover a bit more height just in case, or just write it if it's empty space.
draw.text((360, 495), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((640, 495), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

img.save(out_path)
print(f"Saved {out_path}")
