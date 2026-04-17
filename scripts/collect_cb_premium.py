#!/usr/bin/env python3
"""
일일시황 실시간 데이터 수집기
브라우저 의존 제거 — 공개 API 직접 수집

수집 항목:
1. Coinbase Premium: Binance + Coinbase BTC 가격 비교
2. BTC/ETH OI 24h 변화율: Binance Futures openInterestHist
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
KST = datetime.timezone(datetime.timedelta(hours=9))


def fetch_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_cb_premium():
    """Coinbase Premium = (Coinbase BTC - Binance BTC) / Binance BTC × 100"""
    binance = float(fetch_json("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")["price"])
    coinbase = float(fetch_json("https://api.coinbase.com/v2/prices/BTC-USD/spot")["data"]["amount"])
    premium = (coinbase - binance) / binance * 100
    return premium, coinbase, binance


def get_oi_24h_change(symbol):
    """Binance Futures OI 24시간 변화율"""
    url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=1h&limit=25"
    data = fetch_json(url)
    if len(data) < 25:
        return None
    now_oi = float(data[-1]["sumOpenInterest"])
    past_oi = float(data[0]["sumOpenInterest"])
    if past_oi == 0:
        return None
    return (now_oi - past_oi) / past_oi * 100


def main():
    now = datetime.datetime.now(KST)
    today = now.date().strftime("%Y-%m-%d")

    # 기존 데이터 로드 (ETF, DAT 등 다른 필드 보존)
    existing = {}
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    errors = []

    # 1. CB Premium
    try:
        premium, coinbase, binance = get_cb_premium()
        sign = "+" if premium >= 0 else ""
        existing["cb_premium"] = f"{sign}{premium:.4f}%"
        existing["cb_premium_as_of"] = today
        existing["value"] = existing["cb_premium"]
        existing["cb_premium_detail"] = {
            "coinbase_btc_usd": round(coinbase, 2),
            "binance_btc_usdt": round(binance, 2),
            "premium_pct": round(premium, 4),
            "fetched_at": now.isoformat(),
        }
        print(f"[INFO] CB Premium: {existing['cb_premium']} (Coinbase ${coinbase:,.2f}, Binance ${binance:,.2f})")
    except Exception as e:
        errors.append(f"CB Premium: {e}")
        print(f"[ERROR] CB Premium 수집 실패: {e}", file=sys.stderr)

    # 2. BTC OI 24h
    try:
        btc_oi = get_oi_24h_change("BTCUSDT")
        if btc_oi is not None:
            sign = "+" if btc_oi >= 0 else ""
            existing["btc_oi_24h"] = f"{sign}{btc_oi:.2f}%"
            existing["btc_oi_24h_as_of"] = today
            print(f"[INFO] BTC OI 24h: {existing['btc_oi_24h']}")
    except Exception as e:
        errors.append(f"BTC OI: {e}")
        print(f"[ERROR] BTC OI 수집 실패: {e}", file=sys.stderr)

    # 3. ETH OI 24h
    try:
        eth_oi = get_oi_24h_change("ETHUSDT")
        if eth_oi is not None:
            sign = "+" if eth_oi >= 0 else ""
            existing["eth_oi_24h"] = f"{sign}{eth_oi:.2f}%"
            existing["eth_oi_24h_as_of"] = today
            print(f"[INFO] ETH OI 24h: {existing['eth_oi_24h']}")
    except Exception as e:
        errors.append(f"ETH OI: {e}")
        print(f"[ERROR] ETH OI 수집 실패: {e}", file=sys.stderr)

    # 메타데이터 갱신
    existing["date"] = today
    existing["status"] = "collected" if not errors else "partial"

    # 원자적 쓰기
    fd, tmp = tempfile.mkstemp(dir=WORKSPACE, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OUTPUT)
    except Exception:
        os.unlink(tmp)
        raise

    print(f"[INFO] 저장 완료: {OUTPUT}")
    if errors:
        print(f"[WARN] 일부 실패: {errors}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
