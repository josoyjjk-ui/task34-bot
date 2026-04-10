#!/usr/bin/env python3
"""
Coinbase Premium Index 수집기
Starchild 브라우저 의존 제거 — Binance + Coinbase 공개 API 직접 계산
Premium = (Coinbase BTC/USD - Binance BTC/USDT) / Binance BTC/USDT × 100
"""

import json
import os
import sys
import tempfile
import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

WORKSPACE = "/Users/fireant/.openclaw/workspace"
OUTPUT = os.path.join(WORKSPACE, "cb_premium_input.json")

def fetch_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def get_binance_btc():
    data = fetch_json("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    return float(data["price"])

def get_coinbase_btc():
    data = fetch_json("https://api.coinbase.com/v2/prices/BTC-USD/spot")
    return float(data["data"]["amount"])

def main():
    today = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

    try:
        binance = get_binance_btc()
        coinbase = get_coinbase_btc()
    except (URLError, HTTPError, KeyError, ValueError) as e:
        print(f"[ERROR] API 호출 실패: {e}", file=sys.stderr)
        # fallback: 기존 파일 유지
        if os.path.exists(OUTPUT):
            print("[INFO] 기존 cb_premium_input.json 유지")
        sys.exit(1)

    premium = (coinbase - binance) / binance * 100
    sign = "+" if premium >= 0 else ""
    premium_str = f"{sign}{premium:.4f}%"

    # 기존 데이터 로드 (다른 필드 보존)
    existing = {}
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # 업데이트
    existing["date"] = today
    existing["status"] = "collected"
    existing["cb_premium"] = premium_str
    existing["value"] = premium_str
    existing["cb_premium_detail"] = {
        "coinbase_btc_usd": round(coinbase, 2),
        "binance_btc_usdt": round(binance, 2),
        "premium_pct": round(premium, 4),
        "fetched_at": now.isoformat()
    }

    # 원자적 쓰기
    fd, tmp = tempfile.mkstemp(dir=WORKSPACE, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OUTPUT)
    except Exception:
        os.unlink(tmp)
        raise

    print(f"[INFO] CB Premium: {premium_str}")
    print(f"  Coinbase BTC/USD: ${coinbase:,.2f}")
    print(f"  Binance BTC/USDT: ${binance:,.2f}")
    print(f"  저장: {OUTPUT}")

if __name__ == "__main__":
    main()
