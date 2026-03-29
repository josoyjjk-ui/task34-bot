#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0"]
# ///
"""
불개미 일일시황 이미지 생성기 (HTML + Chrome headless 방식)
- 데이터 수집: SoSoValue(ETF, DAT), Coinalyze(OI), Starchild(CB 프리미엄)
- 이미지 생성: HTML 템플릿 → Chrome headless 스크린샷
- 출력: /Users/fireant/.openclaw/workspace/daily-report-latest.png
"""
import sys, os, subprocess, json, time
from datetime import datetime

# ── 인자 파싱 ──────────────────────────────────────────────
args = sys.argv[1:]
def A(key, default=None):
    try: return args[args.index(key)+1]
    except: return default

# 수동 오버라이드 (크론잡 시 생략 가능)
btc_etf    = A("BTC_ETF")
eth_etf    = A("ETH_ETF")
btc_oi_24h = A("BTC_OI_24H")
eth_oi_24h = A("ETH_OI_24H")
dat_now    = A("DAT_NOW")
cb_premium = A("CB_PREMIUM")
date_str   = A("DATE", datetime.now().strftime("%Y.%m.%d (KST)"))

OUTPUT     = "/Users/fireant/.openclaw/workspace/daily-report-latest.png"
HTML_OUT   = "/Users/fireant/.openclaw/workspace/daily-report-latest.html"

# ── 유틸 ──────────────────────────────────────────────────
def color_class(val_str):
    """값의 부호에 따라 CSS 클래스 반환"""
    if val_str is None: return "white"
    s = val_str.strip()
    if s.startswith("-") or s.startswith("(-"):
        return "red"
    elif s.startswith("+") or (s and s[0].isdigit() and not s.startswith("0.000")):
        return "green"
    return "white"

def arrow(val_str):
    if val_str is None: return ""
    s = val_str.strip()
    if s.startswith("-") or s.startswith("(-"): return " ↓"
    if s.startswith("+"): return " ↑"
    return ""

# ── 데이터 수집 (인자 없을 때만) ───────────────────────────
def fetch_sosovalue_btc():
    import urllib.request
    # JavaScript 렌더링 필요 — AppleScript로 Chrome 활용
    script = """
import subprocess, time, json
result = subprocess.run(
    ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
     '--headless=new', '--disable-gpu', '--no-sandbox',
     '--dump-dom', 'https://sosovalue.com/assets/etf/us-btc-spot'],
    capture_output=True, text=True, timeout=30
)
import re
m = re.search(r'Daily Total Net Inflow.*?(-?\\$[\\d,.]+[MBK])', result.stdout)
print(m.group(1) if m else 'N/A')
"""
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45)
    return r.stdout.strip() or "N/A"

# Playwright 없이 JS 렌더링 필요한 페이지는 크론잡 systemEvent로 수집
# 크론잡에서 브라우저로 수집 후 파일에 저장된 값 사용
def load_collected_data():
    """크론잡이 미리 수집해둔 데이터 파일 로드"""
    path = "/Users/fireant/.openclaw/workspace/cb_premium_input.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# ── HTML 생성 ──────────────────────────────────────────────
def make_html(btc_etf, eth_etf, btc_oi_24h, eth_oi_24h, dat_now, cb_premium, date_str):
    btc_color = color_class(btc_etf)
    eth_color = color_class(eth_etf)
    btc_oi_color = color_class(btc_oi_24h)
    eth_oi_color = color_class(eth_oi_24h)
    dat_color = color_class(dat_now)
    cb_color = color_class(cb_premium)

    btc_arr = arrow(btc_etf)
    eth_arr = arrow(eth_etf)
    btc_oi_arr = arrow(btc_oi_24h)
    eth_oi_arr = arrow(eth_oi_24h)

    # 값 포맷 (괄호 형태로 통일)
    def fmt_etf(v):
        if v is None: return "—"
        v = v.strip()
        if not v.startswith("("): v = f"({v})"
        return v

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1200px;
    height: 700px;
    background-color: #1a4a1a;
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    display: flex;
    flex-direction: column;
    padding: 24px 28px 24px 28px;
  }}
  .title-row {{
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    margin-bottom: 20px;
  }}
  .logo {{
    position: absolute;
    left: 0;
    font-size: 42px;
    line-height: 1;
  }}
  .title-text {{
    font-size: 68px;
    font-weight: 900;
    color: #FFE600;
    letter-spacing: -1px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.4);
  }}
  .date-text {{
    position: absolute;
    right: 0;
    bottom: 6px;
    font-size: 26px;
    color: #ffffff;
    font-weight: 600;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 14px;
    flex: 1;
  }}
  .box {{
    background-color: #0f3a0f;
    border: 3px solid #2d6a2d;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    padding: 18px 28px;
  }}
  .box-header {{
    font-size: 34px;
    font-weight: 800;
    color: #FFE600;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }}
  .box-sub {{
    font-size: 16px;
    color: #aaaaaa;
    margin-bottom: 10px;
    letter-spacing: 0;
  }}
  .data-line {{
    font-size: 30px;
    font-weight: 700;
    line-height: 1.5;
  }}
  .red {{ color: #FF4444; }}
  .green {{ color: #44FF44; }}
  .white {{ color: #ffffff; }}
  .center-box {{
    align-items: center;
    text-align: center;
  }}
  .center-box .box-header {{ text-align: center; }}
  .center-box .data-line {{ text-align: center; }}
</style>
</head>
<body>
  <div class="title-row">
    <div class="logo">🔥🐜</div>
    <div class="title-text">불개미 일일시황</div>
    <div class="date-text">{date_str}</div>
  </div>

  <div class="grid">
    <!-- TOP LEFT: ETF -->
    <div class="box">
      <div class="box-header">BTC ETH ETF 유출입</div>
      <div class="box-sub">ETF 데이터는 마지막 거래일 기준</div>
      <div class="data-line {btc_color}">BTC {fmt_etf(btc_etf)}{btc_arr}</div>
      <div class="data-line {eth_color}">ETH {fmt_etf(eth_etf)}{eth_arr}</div>
    </div>

    <!-- TOP RIGHT: OI -->
    <div class="box center-box">
      <div class="box-header">미결제약정 추이</div>
      <div class="data-line {btc_oi_color}">BTC 24시간 : {btc_oi_24h or '—'}{btc_oi_arr}</div>
      <div class="data-line {eth_oi_color}">ETH 24시간 : {eth_oi_24h or '—'}{eth_oi_arr}</div>
    </div>

    <!-- BOTTOM LEFT: DAT -->
    <div class="box center-box">
      <div class="box-header">DAT 추이</div>
      <div class="data-line {dat_color}">WEEKLY NET INFLOW : {dat_now or '—'}</div>
    </div>

    <!-- BOTTOM RIGHT: CB Premium -->
    <div class="box center-box">
      <div class="box-header">코인베이스 프리미엄</div>
      <div class="data-line {cb_color}">현재 지수 : {cb_premium or '—'}</div>
    </div>
  </div>
</body>
</html>"""
    return html

# ── 스크린샷 ──────────────────────────────────────────────
def screenshot_html(html_path, output_path):
    r = subprocess.run([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1200,700",
        f"--screenshot={output_path}",
        "--hide-scrollbars",
        html_path
    ], capture_output=True, text=True, timeout=30)
    if not os.path.exists(output_path):
        raise Exception(f"스크린샷 실패: {r.stderr[:200]}")

# ── 메인 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 인자로 안 넘어온 값은 크론잡 수집 데이터에서 로드
    collected = load_collected_data()

    if btc_etf    is None: btc_etf    = collected.get("btc_etf",    "—")
    if eth_etf    is None: eth_etf    = collected.get("eth_etf",    "—")
    if btc_oi_24h is None: btc_oi_24h = collected.get("btc_oi_24h", "—")
    if eth_oi_24h is None: eth_oi_24h = collected.get("eth_oi_24h", "—")
    if dat_now    is None: dat_now    = collected.get("dat_now",    "—")
    if cb_premium is None: cb_premium = collected.get("cb_premium", "—")

    print(f"📊 데이터: BTC_ETF={btc_etf} ETH_ETF={eth_etf} BTC_OI={btc_oi_24h} ETH_OI={eth_oi_24h} DAT={dat_now} CB={cb_premium}")

    html = make_html(btc_etf, eth_etf, btc_oi_24h, eth_oi_24h, dat_now, cb_premium, date_str)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    screenshot_html(HTML_OUT, OUTPUT)
    size = os.path.getsize(OUTPUT)
    print(f"✅ 저장: {OUTPUT} ({size//1024}K)")
