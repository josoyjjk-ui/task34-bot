#!/usr/bin/env python3
"""
일일시황 이미지 Pillow 직접 렌더링
숫자 정확히 표시 보장 (AI 생성 금지)
"""

from PIL import Image, ImageDraw, ImageFont
import os
import sys

# ── 출력 경로 ──────────────────────────────────────────────
OUTPUT_PATH = "/Users/fireant/.openclaw/workspace/daily-report-latest.png"

# ── 캔버스 설정 ────────────────────────────────────────────
W, H = 1280, 720
BG_COLOR       = (30, 61, 15)    # #1e3d0f 어두운 초록
BOX_COLOR      = (45, 90, 27)    # #2d5a1b 박스 배경
BOX_BORDER     = (255, 255, 255) # 흰색 테두리
YELLOW         = (255, 220, 50)
WHITE          = (255, 255, 255)
RED            = (255, 80, 80)
GREEN          = (80, 220, 80)
GRAY           = (200, 200, 200)

# ── 폰트 로더 ──────────────────────────────────────────────
def load_font(size, bold=False):
    candidates = [
        # macOS Korean fonts
        "/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NanumGothicBold.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        # fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    # NanumGothicBold for bold, NanumGothic for regular
    if bold:
        priority = [
            "/Library/Fonts/NanumGothicBold.ttf",
            "/Library/Fonts/NanumGothicExtraBold.ttf",
        ] + candidates
    else:
        priority = candidates

    for path in priority:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # ultimate fallback
    return ImageFont.load_default()

# ── 텍스트 그리기 헬퍼 ────────────────────────────────────
def draw_text(draw, x, y, text, font, color):
    draw.text((x, y), text, font=font, fill=color)

def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

def text_height(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]

# ── 박스 그리기 ────────────────────────────────────────────
def draw_box(draw, x, y, w, h):
    # 배경
    draw.rectangle([x, y, x+w, y+h], fill=BOX_COLOR)
    # 테두리 (2px)
    draw.rectangle([x, y, x+w, y+h], outline=BOX_BORDER, width=2)

# ── 메인 렌더링 ────────────────────────────────────────────
def render():
    img  = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 폰트 크기 세트
    f_title_big  = load_font(52, bold=True)   # 헤더 제목
    f_title_med  = load_font(36)              # 헤더 날짜
    f_box_title  = load_font(30, bold=True)   # 박스 제목
    f_box_sub    = load_font(18)              # 박스 부제
    f_box_data   = load_font(28)              # 박스 데이터
    f_box_data_sm= load_font(24)              # 박스 데이터 (작은)

    # ── 헤더 영역 ──────────────────────────────────────────
    HEADER_H = 80
    PAD_X    = 40

    # 좌: 불개미 일일시황
    draw_text(draw, PAD_X, 12, "불개미 일일시황", f_title_big, YELLOW)

    # 우: 2026.03.20 (KST)
    date_text = "2026.03.20 (KST)"
    dw = text_width(draw, date_text, f_title_med)
    draw_text(draw, W - PAD_X - dw, 22, date_text, f_title_med, WHITE)

    # 구분선
    draw.line([(PAD_X, HEADER_H), (W - PAD_X, HEADER_H)], fill=WHITE, width=2)

    # ── 2x2 그리드 박스 ───────────────────────────────────
    MARGIN   = 30   # 박스 간 여백 및 외부 여백
    TOP      = HEADER_H + MARGIN
    BOX_W    = (W - MARGIN * 3) // 2   # 두 박스 + 세 여백(좌/중/우)
    BOX_H    = (H - TOP - MARGIN * 2) // 2
    PAD      = 20   # 박스 내부 패딩

    boxes = [
        (MARGIN,          TOP),             # 박스1 좌상단
        (MARGIN*2+BOX_W,  TOP),             # 박스2 우상단
        (MARGIN,          TOP+BOX_H+MARGIN),# 박스3 좌하단
        (MARGIN*2+BOX_W,  TOP+BOX_H+MARGIN),# 박스4 우하단
    ]

    for bx, by in boxes:
        draw_box(draw, bx, by, BOX_W, BOX_H)

    # ── 박스 1: BTC ETH ETF 유출입 ───────────────────────
    bx, by = boxes[0]
    cx = bx + PAD
    cy = by + PAD

    draw_text(draw, cx, cy, "BTC ETH ETF 유출입", f_box_title, YELLOW)
    cy += text_height(draw, "A", f_box_title) + 6
    draw_text(draw, cx, cy, "ETF 데이터는 마지막 거래일 기준", f_box_sub, GRAY)
    cy += text_height(draw, "A", f_box_sub) + 14
    draw_text(draw, cx, cy, "BTC (-$90.19M)", f_box_data, RED)
    cy += text_height(draw, "A", f_box_data) + 8
    draw_text(draw, cx, cy, "ETH (-$131.16M)", f_box_data, RED)

    # ── 박스 2: 미결제약정 추이 ───────────────────────────
    bx, by = boxes[1]
    cx = bx + PAD
    cy = by + PAD

    draw_text(draw, cx, cy, "미결제약정 추이", f_box_title, YELLOW)
    cy += text_height(draw, "A", f_box_title) + 18
    draw_text(draw, cx, cy, "BTC 24시간 : +0.20%", f_box_data, GREEN)
    cy += text_height(draw, "A", f_box_data) + 8
    draw_text(draw, cx, cy, "ETH 24시간 : -0.86%", f_box_data, RED)

    # ── 박스 3: DAT 추이 ──────────────────────────────────
    bx, by = boxes[2]
    cx = bx + PAD
    cy = by + PAD

    draw_text(draw, cx, cy, "DAT 추이", f_box_title, YELLOW)
    cy += text_height(draw, "A", f_box_title) + 18
    draw_text(draw, cx, cy, "WEEKLY NET INFLOW :", f_box_data_sm, WHITE)
    cy += text_height(draw, "A", f_box_data_sm) + 8
    draw_text(draw, cx, cy, "$1.57B (22,341 BTC)", f_box_data, GREEN)

    # ── 박스 4: 코인베이스 프리미엄 ──────────────────────
    bx, by = boxes[3]
    cx = bx + PAD
    cy = by + PAD

    draw_text(draw, cx, cy, "코인베이스 프리미엄", f_box_title, YELLOW)
    cy += text_height(draw, "A", f_box_title) + 18
    draw_text(draw, cx, cy, "현재 지수 : -0.015%", f_box_data, RED)

    # ── 저장 ──────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    img.save(OUTPUT_PATH, "PNG")
    print(f"✅ 이미지 저장 완료: {OUTPUT_PATH}")
    return OUTPUT_PATH

if __name__ == "__main__":
    path = render()
    sys.exit(0)
