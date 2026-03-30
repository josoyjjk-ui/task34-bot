import sys
from PIL import Image, ImageDraw, ImageFont

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_patched2.png"

try:
    img = Image.open(img_path).convert("RGB")
except Exception as e:
    print(f"Image load failed: {e}")
    sys.exit(1)

draw = ImageDraw.Draw(img)

def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()

FONT_KO_BOLD = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FONT_CHALK_BOLD = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
FONT_CHALK_REGULAR = "/System/Library/Fonts/Supplemental/Chalkboard.ttc"

# We want to patch the exact strings to match the requirements.
# Requirement 2: "BTC ETH 유출입"
f_title_lg = load_font(FONT_KO_BOLD, 75, 3) 
# I will use a crop of the background chalkboard (e.g. from x=700, y=700) to patch over the text instead of a solid rectangle, for better realism.
bg_patch = img.crop((700, 700, 1400, 900)) # 700x200

# Cover "BTC·ETH ETF 유출입" area: [120, 30, 800, 130]
patch_top = bg_patch.resize((680, 100))
img.paste(patch_top, (120, 30))

draw.text((150, 45), "BTC ETH 유출입", font=f_title_lg, fill=(240, 240, 200))

# Now patch the ETH area:
# "ETH (+52M)"
# "Total +52M 블랙록 +32M 피델리티 +15M"
# This area is roughly [100, 320, 800, 500]
patch_bottom = bg_patch.resize((700, 180))
img.paste(patch_bottom, (100, 320))

f_header = load_font(FONT_CHALK_BOLD, 65, 1)
draw.text((250, 330), "ETH (+36M)", font=f_header, fill=(255, 220, 50))

f_sm = load_font(FONT_KO_BOLD, 50, 3)
draw.text((120, 410), "피델리티 +35M", font=f_sm, fill=(255, 255, 255))
draw.text((450, 410), "비트와이즈 +32M", font=f_sm, fill=(255, 255, 255))

# Also I need to patch the BTC numbers because maybe they were different, but +199M matches.
# Wait, let's just make sure we are not covering "(ETF 데이터는 마지막 거래일 기준)" which is around y=135.
# My first patch went up to y=130, so it should be fine.

img.save(out_path)
print(f"Saved to {out_path}")
