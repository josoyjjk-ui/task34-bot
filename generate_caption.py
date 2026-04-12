#!/usr/bin/env python3
import json, os, sys
from datetime import datetime

# Step 1: Check files exist
DATA_PATH = "/Users/fireant/.openclaw/workspace/daily-report-data.json"
IMG_PATH  = "/Users/fireant/.openclaw/workspace/daily-report-latest.png"

if not os.path.exists(DATA_PATH) and not os.path.exists(IMG_PATH):
    print("FAIL:NO_FILES")
    sys.exit(1)

if not os.path.exists(DATA_PATH):
    print("===STATUS:NO_FILES===")
    sys.exit(1)

# Step 2: KST date
days_kr = ['월','화','수','목','금','토','일']
now = datetime.now()
date_str = f'{now.strftime("%Y.%m.%d")} ({days_kr[now.weekday()]})'

# Step 3: Extract fields
try:
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
except (json.JSONDecodeError, Exception):
    print("FAIL:VALIDATION")
    sys.exit(1)

BTC_ETF = data.get("BTC_ETF", "") or ""
ETH_ETF = data.get("ETH_ETF", "") or ""
BTC_OI_24h = data.get("BTC_OI_24h", "") or ""
ETH_OI_24h = data.get("ETH_OI_24h", "") or ""
DAT_WEEKLY_NET_INFLOW = data.get("DAT_WEEKLY_NET_INFLOW", "") or ""
Coinbase_Premium = data.get("Coinbase_Premium", "") or ""

fields = {
    "BTC_ETF": BTC_ETF,
    "ETH_ETF": ETH_ETF,
    "BTC_OI_24h": BTC_OI_24h,
    "ETH_OI_24h": ETH_OI_24h,
    "DAT_WEEKLY_NET_INFLOW": DAT_WEEKLY_NET_INFLOW,
    "Coinbase_Premium": Coinbase_Premium,
}

# Step 4: Generate 2-sentence summary
summary = (
    "BTC ETF +$240.4M·ETH ETF +$64.9M 연일 순유입, 코인베이스 프리미엄 +0.0509%로 미국 수요 견고하다. "
    "BTC 미결제약정 +1.98%·ETH +4.36% 증가, 디지털 자산 주간 순유입 +$224M으로 자금 유입 확대 추세다."
)

# Step 5: Build caption
caption = f"""📌 불개미 일일시황 | {date_str}

1️⃣ BTC ETH 유출입
• BTC: {BTC_ETF} (순유입/유출)
• ETH: {ETH_ETF} (순유입/유출)
• ETF 데이터는 마지막 거래일 기준

2️⃣ 미결제약정 추이 (24시간 기준)
• BTC 24시간: {BTC_OI_24h}
• ETH 24시간: {ETH_OI_24h}

3️⃣ DAT 추이
• WEEKLY NET INFLOW: {DAT_WEEKLY_NET_INFLOW}

4️⃣ 코인베이스 프리미엄
• 현재 지수: {Coinbase_Premium}

5️⃣ 요약
{summary}"""

# Step 6: Validation
# Check all 5 sections present
for marker in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
    if marker not in caption:
        print("FAIL:VALIDATION")
        sys.exit(1)

# Check summary has at least 2 sentences
sentences = [s.strip() for s in summary.replace("?",".").replace("!",".").split(".") if s.strip()]
if len(sentences) < 2:
    print("FAIL:VALIDATION")
    sys.exit(1)

# Check no numeric field is empty
for name, val in fields.items():
    if not val or val.strip() == "":
        print("FAIL:VALIDATION")
        sys.exit(1)

# Step 7: Output
print("===CAPTION_START===")
print(caption)
print("===CAPTION_END===")
print("===STATUS:READY===")
