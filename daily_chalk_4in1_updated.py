import os, sys
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

BASE    = "/Users/fireant/.openclaw/workspace/assets/fireant-chalkboard-base.jpg"
LOGO    = "/Users/fireant/.openclaw/workspace/assets/fireant-logo-nobg.png"
OUTPUT  = "/Users/fireant/.openclaw/workspace/fireant_daily_chalk_latest.png"

FONT_CHALK_BOLD    = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
FONT_CHALK_REGULAR = "/System/Library/Fonts/Supplemental/Chalkboard.ttc"
FONT_KO_BOLD       = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

WHITE   = (255, 255, 255)
YELLOW  = (255, 220, 50)
GREEN   = (80, 220, 100)
RED     = (255, 90, 90)
CHALK_TITLE = (240, 240, 200)
CHALK_DIM   = (170, 200, 170)

def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()

def color_for(val_str: str):
    s = str(val_str).strip()
    if s.startswith('+'): return GREEN
    elif s.startswith('-'): return RED
    return WHITE

def draw_chalk_line(draw, x1, y1, x2, y2, color=(255,255,255,160), width=1):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

def generate_image(data: dict) -> str:
    img = Image.open(BASE).convert("RGBA")
    W, H = img.size

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    f_title_lg   = load_font(FONT_KO_BOLD, 30, 3)
    f_title_sm   = load_font(FONT_KO_BOLD, 22, 3)
    f_header     = load_font(FONT_CHALK_BOLD, 26, 1)
    f_data       = load_font(FONT_CHALK_REGULAR, 22, 0)
    f_label      = load_font(FONT_KO_BOLD, 20, 3)
    f_top_title  = load_font(FONT_KO_BOLD, 45, 3)
    f_top_date   = load_font(FONT_CHALK_REGULAR, 24, 0)
    f_note       = load_font(FONT_KO_BOLD, 16, 0)

    try:
        logo = Image.open(LOGO).convert("RGBA")
        lw, lh = 70, 70
        logo = logo.resize((lw, lh), Image.LANCZOS)
        overlay.paste(logo, (20, 20), logo)
    except Exception:
        pass

    title_text = "불개미 일일시황"
    date_text  = data["date"] + " (KST)"
    tw = draw.textlength(title_text, font=f_top_title)
    draw.text((W - tw - 30, 20), title_text, font=f_top_title, fill=WHITE)
    dw = draw.textlength(date_text, font=f_top_date)
    draw.text((W - dw - 30, 75), date_text, font=f_top_date, fill=CHALK_DIM)

    BX1, BX2 = 100, 1180
    BY1, BY2 = 130, 680
    BW = BX2 - BX1
    BH = BY2 - BY1
    GAP = 40
    col_w = (BW - GAP) // 2
    row_h = (BH - GAP) // 2

    sections = [
        (BX1,           BY1),
        (BX1+col_w+GAP, BY1),
        (BX1,           BY1+row_h+GAP),
        (BX1+col_w+GAP, BY1+row_h+GAP),
    ]

    mid_x = BX1 + col_w + GAP // 2
    mid_y = BY1 + row_h + GAP // 2
    draw_chalk_line(draw, mid_x, BY1, mid_x, BY2, width=2)
    draw_chalk_line(draw, BX1, mid_y, BX2, mid_y, width=2)

    # 1: ETF
    sx, sy = sections[0]
    sw, sh = col_w, row_h
    draw.text((sx, sy), "BTC ETH 유출입", font=f_title_lg, fill=CHALK_TITLE)
    draw.text((sx, sy+35), "(ETF 데이터는 마지막 거래일 기준)", font=f_note, fill=CHALK_DIM)

    etf = data["etf"]
    col1_x = sx
    col2_x = sx + sw // 2 + 10

    draw.text((col1_x, sy+60), f"BTC ({etf['btc_total']})", font=f_header, fill=color_for(etf['btc_total']))
    draw.text((col2_x, sy+60), f"ETH ({etf['eth_total']})", font=f_header, fill=color_for(etf['eth_total']))
    draw_chalk_line(draw, sx, sy+95, sx+sw, sy+95, width=1)

    row_spacing = 28
    for i, (fname, fval) in enumerate(etf["btc"][:4]):
        y_ = sy + 105 + i * row_spacing
        draw.text((col1_x, y_), fname, font=f_label, fill=WHITE)
        vw = draw.textlength(fval, font=f_data)
        draw.text((col1_x + sw//2 - 20 - vw, y_), fval, font=f_data, fill=color_for(fval))

    for i, (fname, fval) in enumerate(etf["eth"][:4]):
        y_ = sy + 105 + i * row_spacing
        draw.text((col2_x, y_), fname, font=f_label, fill=WHITE)
        vw = draw.textlength(fval, font=f_data)
        draw.text((col2_x + sw//2 - 20 - vw, y_), fval, font=f_data, fill=color_for(fval))

    # 2: OI
    sx, sy = sections[1]
    oi = data["oi"]
    draw.text((sx, sy), "미결제약정 추이", font=f_title_lg, fill=CHALK_TITLE)
    
    draw.text((sx, sy+50), "BTC", font=f_title_sm, fill=YELLOW)
    draw.text((sx, sy+85), f"24h: {oi['btc_24h']}", font=f_data, fill=color_for(oi['btc_24h']))
    draw.text((sx, sy+120), f"72h: {oi['btc_72h']}", font=f_data, fill=color_for(oi['btc_72h']))

    draw.text((sx+sw//2, sy+50), "ETH", font=f_title_sm, fill=YELLOW)
    draw.text((sx+sw//2, sy+85), f"24h: {oi['eth_24h']}", font=f_data, fill=color_for(oi['eth_24h']))
    draw.text((sx+sw//2, sy+120), f"72h: {oi['eth_72h']}", font=f_data, fill=color_for(oi['eth_72h']))

    # 3: DAT
    sx, sy = sections[2]
    dat = data["dat"]
    draw.text((sx, sy), "DAT 추이", font=f_title_lg, fill=CHALK_TITLE)
    
    draw.text((sx, sy+50), "BTC", font=f_title_sm, fill=YELLOW)
    draw.text((sx, sy+85), f"24h: {dat['btc_24h']}", font=f_data, fill=color_for(dat['btc_24h']))
    draw.text((sx, sy+120), f"72h: {dat['btc_72h']}", font=f_data, fill=color_for(dat['btc_72h']))

    draw.text((sx+sw//2, sy+50), "ETH", font=f_title_sm, fill=YELLOW)
    draw.text((sx+sw//2, sy+85), f"24h: {dat['eth_24h']}", font=f_data, fill=color_for(dat['eth_24h']))
    draw.text((sx+sw//2, sy+120), f"72h: {dat['eth_72h']}", font=f_data, fill=color_for(dat['eth_72h']))

    # 4: Coinbase
    sx, sy = sections[3]
    cb = data["cb_premium"]
    draw.text((sx, sy), "코인베이스 프리미엄", font=f_title_lg, fill=CHALK_TITLE)
    
    draw.text((sx, sy+60), f"24h: {cb['val_24h']}", font=f_data, fill=color_for(cb['val_24h']))
    draw.text((sx, sy+100), f"72h: {cb['val_72h']}", font=f_data, fill=color_for(cb['val_72h']))

    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(OUTPUT, quality=95)
    print(OUTPUT)

if __name__ == "__main__":
    data = {
        "date": "2026.03.18",
        "etf": {
            "btc_total": "+199M",
            "eth_total": "+36M",
            "btc": [("블랙록", "+139M"), ("피델리티", "+64M"), ("비트와이즈", "+3M"), ("반에크", "-6M")],
            "eth": [("피델리티", "+35M"), ("비트와이즈", "+32M"), ("블랙록", "-16M"), ("그레이스케일", "-15M")],
        },
        "oi": {
            "btc_24h": "+1.6%", "btc_72h": "+5.1%",
            "eth_24h": "+2.1%", "eth_72h": "+3.8%",
        },
        "dat": {
            "btc_24h": "+0.9%", "btc_72h": "+0.8%",
            "eth_24h": "+1.1%", "eth_72h": "+1.5%",
        },
        "cb_premium": {
            "val_24h": "+0.02%",
            "val_72h": "-0.01%",
        },
    }
    generate_image(data)
