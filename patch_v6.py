import sys
from PIL import Image, ImageDraw, ImageFont

img_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_etf_note.png"
out_path = "/Users/fireant/.openclaw/workspace/fireant_chalkboard_v6_patched.png"

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
f_title_lg = load_font(FONT_KO_BOLD, 38, 3) 

BG_COLOR = (32, 38, 42)

# Get image size
w, h = img.size
print(f"Image size: {w}x{h}")

# The text "BTC·ETF ETF 유출입" is likely around x=100-500, y=50-130
# " (ETF 데이터는 마지막 거래일 기준)" is right below it, maybe y=130-150.
# So I'll just draw over y=50 to 125.
draw.rectangle([100, 50, 480, 125], fill=BG_COLOR)
draw.text((120, 65), "BTC ETH 유출입", font=f_title_lg, fill=(240, 240, 200))

# Overwrite ETH numbers:
# "ETH (+52M)" is roughly in the middle-left.
# Let's cover from y=380 to 480
draw.rectangle([50, 380, 490, 480], fill=BG_COLOR)
f_header = load_font(FONT_KO_BOLD, 30, 3)
draw.text((160, 385), "ETH (+36M)", font=f_header, fill=(255, 220, 50))
f_sm = load_font(FONT_KO_BOLD, 22, 3)
draw.text((60, 430), "피델리티 +35M   비트와이즈 +32M", font=f_sm, fill=(255, 255, 255))
draw.text((60, 470), "블랙록 -16M   그레이스케일 -15M", font=f_sm, fill=(255, 255, 255))

img.save(out_path)
print(f"Saved to {out_path}")
