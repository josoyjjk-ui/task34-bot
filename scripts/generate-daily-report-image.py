#!/usr/bin/env python3
"""
불개미 일일시황 칠판 이미지 생성기 v2 (1408x768)
- 레퍼런스 기반 레이아웃/색상/분필 효과
- CLI 인수로 모든 값 주입
- 출력: daily-report-preview2.png
"""
from __future__ import annotations

import argparse, json, random, math
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1408, 768
OUT_PATH = Path(__file__).resolve().parent.parent / 'daily-report-latest.png'

# ── Fonts ──────────────────────────────────────────────────────────
# ChalkboardSE는 한글 glyph 없음 (두부 렌더링) → AppleSDGothicNeo 사용
KOR_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
ENG_FONT = "/System/Library/Fonts/Supplemental/Chalkduster.ttf"
FALLBACK = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

def _font(path, size, idx=0):
    try:
        return ImageFont.truetype(path, size=size, index=idx)
    except Exception:
        try:
            return ImageFont.truetype(FALLBACK, size=size)
        except Exception:
            return ImageFont.load_default()

def font_kor(size): return _font(KOR_FONT, size, 0)
def font_eng(size): return _font(ENG_FONT, size)

# ── Colors (reference-matched) ─────────────────────────────────────
COL_YELLOW  = (255, 240, 80)    # 레퍼런스: 밝은 노랑
COL_WHITE   = (250, 250, 248)   # 레퍼런스: 거의 순백 (251,251,250)
COL_GRAY    = (180, 185, 190)
COL_GREEN   = (85, 225, 90)     # 레퍼런스: (81,221,86)
COL_RED     = (255, 90, 80)
COL_BORDER  = (65, 145, 72)     # 적당한 초록 테두리
COL_BG      = (24, 58, 33)      # 레퍼런스 정확히 매칭

# ── Chalkboard background ─────────────────────────────────────────
def make_chalkboard(w, h):
    rng = np.random.RandomState(42)
    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:, :, 0] = 24; base[:, :, 1] = 58; base[:, :, 2] = 33

    # Vignette
    Y, X = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    vig = np.clip(1.0 - dist * 0.15, 0.80, 1.0)
    for c in range(3):
        base[:, :, c] *= vig

    # Fine noise (chalk dust on board)
    noise = rng.normal(0, 5, (h, w, 3)).astype(np.float32)
    base += noise

    # Horizontal wood-grain streaks
    for _ in range(60):
        y0 = rng.randint(0, h)
        thickness = rng.randint(1, 4)
        shift = rng.uniform(-3, 3)
        y1 = min(y0 + thickness, h)
        base[y0:y1, :, :] += shift

    # (smudges removed — clean board)

    base = np.clip(base, 0, 255).astype(np.uint8)
    img = Image.fromarray(base, 'RGB')
    # Slight gaussian for blending
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    return img

# ── Chalk text renderer ────────────────────────────────────────────
def chalk_text(canvas, xy, text, font, color, glow=True, particles=False, anchor=None, stroke=2):
    """Render bold, bright text with stroke for max readability."""
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ax, ay = xy
    if anchor:
        if 'r' in anchor:
            ax = ax - tw
        elif 'm' in anchor:
            ax = ax - tw // 2
    x, y = ax, ay

    d = ImageDraw.Draw(canvas)
    d.text((x, y), text, font=font, fill=color,
           stroke_width=stroke, stroke_fill=color)

    return canvas

# ── Panel border (chalk style) ─────────────────────────────────────
def draw_panel(canvas, x1, y1, x2, y2, color=COL_BORDER):
    """Draw rounded panel border."""
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=12, outline=color, width=2
    )
    return canvas

# ── Color helper ────────────────────────────────────────────────────
def val_color(val_str):
    s = val_str.strip()
    return COL_GREEN if s.startswith('+') else COL_RED if s.startswith('-') else COL_WHITE

# ── Main build ─────────────────────────────────────────────────────
def build_image(args):
    random.seed(42)
    canvas = make_chalkboard(W, H)  # RGB

    # Panel coordinates (reference-matched)
    LX1, LX2 = 30, 680
    RX1, RX2 = 728, 1378
    TY1, TY2 = 125, 430
    BY1, BY2 = 455, 748

    for box in [(LX1, TY1, LX2, TY2), (RX1, TY1, RX2, TY2),
                (LX1, BY1, LX2, BY2), (RX1, BY1, RX2, BY2)]:
        canvas = draw_panel(canvas, *box)

    # Fonts
    f_title     = font_kor(80)
    f_date      = font_kor(54)
    f_box_title = font_kor(46)
    f_sub       = font_kor(22)
    f_value     = font_kor(52)   # 한글/영어 레이블
    f_num       = font_kor(60)   # 숫자 데이터 (+15%)
    f_dat       = font_kor(38)
    f_dat_num   = font_kor(44)   # DAT 숫자 (+15%)

    # Title
    canvas = chalk_text(canvas, (32, 22), '불개미 일일시황', f_title, COL_YELLOW)

    # Date (right-aligned)
    canvas = chalk_text(canvas, (W - 32, 35), args.date, f_date, COL_YELLOW, anchor='r')

    # ── Panel 1: ETF (top-left) ────────────────────────────────────
    cx = (LX1 + LX2) // 2
    canvas = chalk_text(canvas, (cx, 155), 'BTC ETH ETF 유출입', f_box_title, COL_WHITE, anchor='m')
    canvas = chalk_text(canvas, (cx, 205), 'ETF 데이터는 마지막 거래일 기준', f_sub, COL_GRAY, glow=False, particles=False, anchor='m', stroke=0)

    btc_c = val_color(args.btc_etf)
    eth_c = val_color(args.eth_etf)
    canvas = chalk_text(canvas, (80, 265), f'BTC ({args.btc_etf})', f_num, btc_c)
    canvas = chalk_text(canvas, (80, 345), f'ETH ({args.eth_etf})', f_num, eth_c)

    # ── Panel 2: OI (top-right) ────────────────────────────────────
    cx_r = (RX1 + RX2) // 2
    canvas = chalk_text(canvas, (cx_r, 165), '미결제약정 추이', f_box_title, COL_YELLOW, anchor='m')

    btc_oi_c = val_color(args.btc_oi)
    eth_oi_c = val_color(args.eth_oi)
    canvas = chalk_text(canvas, (RX1 + 50, 265), f'BTC 24시간 : {args.btc_oi}', f_num, btc_oi_c)
    canvas = chalk_text(canvas, (RX1 + 50, 345), f'ETH 24시간 : {args.eth_oi}', f_num, eth_oi_c)

    # ── Panel 3: DAT (bottom-left) ─────────────────────────────────
    cx2 = (LX1 + LX2) // 2
    canvas = chalk_text(canvas, (cx2, 500), 'DAT 추이', f_box_title, COL_WHITE, anchor='m')
    dat_c = val_color(args.dat)
    canvas = chalk_text(canvas, (70, 595), f'WEEKLY NET INFLOW : {args.dat}', f_dat_num, dat_c)

    # ── Panel 4: CB Premium (bottom-right) ──────────────────────────
    canvas = chalk_text(canvas, (cx_r, 500), '코인베이스 프리미엄', f_box_title, COL_YELLOW, anchor='m')
    cb_c = val_color(args.cb)
    canvas = chalk_text(canvas, (RX1 + 50, 600), f'현재 지수 : {args.cb}', f_num, cb_c)

    # Final save
    final = canvas
    final.save(str(OUT_PATH), format='PNG')
    print(f'✅ saved: {OUT_PATH} ({W}x{H})')


def parse_args():
    json_path = Path(__file__).resolve().parent.parent / 'daily-report-data.json'
    try:
        jd = json.load(open(json_path))
        defaults = {
            'btc_etf': jd.get('BTC_ETF', '+$0M'),
            'eth_etf': jd.get('ETH_ETF', '+$0M'),
            'btc_oi': jd.get('BTC_OI_24h', '+0%'),
            'eth_oi': jd.get('ETH_OI_24h', '+0%'),
            'dat': jd.get('DAT_WEEKLY_NET_INFLOW', '+$0'),
            'cb': jd.get('Coinbase_Premium', '+0%'),
        }
    except:
        defaults = {}

    p = argparse.ArgumentParser(description='불개미 일일시황 칠판 이미지 생성')
    days_kr = ['월','화','수','목','금','토','일']
    now = datetime.now()
    default_date = f"{now.strftime('%Y.%m.%d')} ({days_kr[now.weekday()]})"
    p.add_argument('--date', default=default_date)
    p.add_argument('--btc-etf', dest='btc_etf', default=defaults.get('btc_etf', '+$0M'))
    p.add_argument('--eth-etf', dest='eth_etf', default=defaults.get('eth_etf', '+$0M'))
    p.add_argument('--btc-oi', dest='btc_oi', default=defaults.get('btc_oi', '+0%'))
    p.add_argument('--eth-oi', dest='eth_oi', default=defaults.get('eth_oi', '+0%'))
    p.add_argument('--dat', default=defaults.get('dat', '+$0'))
    p.add_argument('--cb', default=defaults.get('cb', '+0%'))
    return p.parse_args()


if __name__ == '__main__':
    build_image(parse_args())
