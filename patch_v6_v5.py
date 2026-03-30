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

# Crop an empty piece of the chalkboard
empty_patch = img.crop((100, 550, 800, 750)) # 700x200

# 1. Patch Title "BTC·ETF ETF 유출입" [120, 100, 750, 195]
patch1 = empty_patch.resize((630, 95))
img.paste(patch1, (120, 100))

f_title = load_font(FONT_KO_BOLD, 75, 3)
draw.text((150, 110), "BTC ETH 유출입", font=f_title, fill=(240, 240, 200))

# 2. Patch ETH Section [80, 380, 750, 550]
patch2 = empty_patch.resize((670, 170))
img.paste(patch2, (80, 380))

f_eth_header = load_font(FONT_CHALK_BOLD, 65, 1)
draw.text((250, 385), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

f_eth_text = load_font(FONT_KO_BOLD, 50, 3)
draw.text((100, 460), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((360, 460), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((640, 460), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

# Draw the negative values below if we want, or just leave it clean. The original had:
# Total +52M 블랙록 +32M 피델리티 +15M
# We can just use the line above. Let's add BlackRock/Grayscale to be accurate.
draw.text((360, 510), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((640, 510), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

# Wait, the patch2 was only up to y=550. y=510 text will fit inside it.
# Wait, "비트와이즈 +32M" at x=640 might get cut off if patch2 ends at x=750?
# 640 + length of text. Size 50 font. 7 chars = 350px. 640+350 = 990.
# The original had "피델리티 +15M" at the end of the line.
# Let's adjust the x coordinates for ETH details:
# Total: 100
# Fidelity: 320
# Bitwise: 580
# BlackRock: 320
# Grayscale: 580

# Let me redraw those texts properly
patch2 = empty_patch.resize((850, 180)) # wider patch just in case
img.paste(patch2, (80, 380))

draw.text((250, 385), "ETH (+36M)", font=f_eth_header, fill=(255, 220, 50))

draw.text((100, 460), "Total +36M", font=f_eth_text, fill=(255, 255, 255))
draw.text((320, 460), "피델리티 +35M", font=f_eth_text, fill=(80, 220, 100))
draw.text((580, 460), "비트와이즈 +32M", font=f_eth_text, fill=(80, 220, 100))

draw.text((320, 510), "블랙록 -16M", font=f_eth_text, fill=(255, 90, 90))
draw.text((580, 510), "그레이스케일 -15M", font=f_eth_text, fill=(255, 90, 90))

img.save(out_path)
print(f"Saved {out_path}")
