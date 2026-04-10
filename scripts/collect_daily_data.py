#!/usr/bin/env python3
"""
일일시황 데이터 단일 수집 스크립트
- SoSoValue: BTC/ETH ETF 순유입
- Coinglass: BTC/ETH OI 24h, DAT Weekly Net Inflow
- CB Premium: cb_premium_input.json에서 로드
- 원자적 파일 쓰기 + 날짜 검증 + 하위호환 키 유지
"""

import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(WORKSPACE, "daily-report-data.json")
CB_INPUT_FILE = os.path.join(WORKSPACE, "cb_premium_input.json")
TIMEOUT = 15
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def now_kst():
    return datetime.now(KST)


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_html(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fmt_money(val):
    """Format a number as +$XM or -$XM."""
    if val is None:
        return "N/A"
    sign = "+" if val >= 0 else "-"
    abs_val = abs(val)
    if abs_val >= 1e9:
        return f"{sign}${abs_val/1e9:.2f}B"
    return f"{sign}${abs_val/1e6:.1f}M"


def fmt_pct(val):
    """Format a number as +X.XX% or -X.XX%."""
    if val is None:
        return "N/A"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def collect_sosovalue_etf():
    """Scrape SoSoValue for BTC/ETH ETF net flow."""
    results = {}
    now = now_kst()
    fetched = now.isoformat()

    # SoSoValue API endpoints (public, no key needed)
    # Try their public API first
    for coin, key in [("btc", "BTC_ETF"), ("eth", "ETH_ETF")]:
        try:
            url = f"https://api.sosovalue.com/openapi/etf/overview?tokenType={coin}"
            data = fetch_json(url)
            # Navigate the response structure
            if isinstance(data, dict):
                # Try common structures
                net_flow = None
                data_date = now.strftime("%Y-%m-%d")

                # sosovalue returns data in various shapes; try to extract net inflow
                if "data" in data:
                    d = data["data"]
                    if isinstance(d, dict):
                        # look for netInflow or dailyNetFlow
                        for k in ["dailyNetInflow", "netInflow", "dailyNetInflowUsd"]:
                            if k in d:
                                net_flow = d[k]
                                break
                        if "date" in d:
                            data_date = d["date"][:10]

                if net_flow is not None:
                    results[key] = {
                        "value": fmt_money(float(net_flow)),
                        "source": "sosovalue",
                        "data_date": data_date,
                        "fetched_at": fetched,
                    }
                else:
                    print(f"[WARN] sosovalue {coin}: could not parse response", file=sys.stderr)
                    results[key] = None
            else:
                results[key] = None
        except Exception as e:
            print(f"[WARN] sosovalue {coin} ETF fetch failed: {e}", file=sys.stderr)
            results[key] = None

    return results


def collect_coinglass_oi():
    """Fetch BTC/ETH OI 24h change from Coinglass."""
    results = {}
    now = now_kst()
    fetched = now.isoformat()

    for symbol, key in [("BTC", "BTC_OI"), ("ETH", "ETH_OI")]:
        try:
            # Coinglass public API for OI change
            url = f"https://open-api.coinglass.com/public/v2/openInterest?symbol={symbol}&time_type=h24"
            data = fetch_json(url)
            oi_change = None
            data_date = now.strftime("%Y-%m-%d")

            if isinstance(data, dict) and data.get("success"):
                d = data.get("data", [])
                if d and isinstance(d, list):
                    # Get OI 24h change percentage
                    for item in d:
                        if isinstance(item, dict) and "change" in item:
                            oi_change = float(item["change"])
                            break
                        elif isinstance(item, dict) and "oiChange24h" in item:
                            oi_change = float(item["oiChange24h"])
                            break
            elif isinstance(data, dict):
                # Try alternate structure
                d = data.get("data", {})
                if isinstance(d, dict):
                    for k in ["change24h", "oiChange24h", "change"]:
                        if k in d:
                            oi_change = float(d[k])
                            break

            if oi_change is not None:
                results[key] = {
                    "value": fmt_pct(oi_change),
                    "source": "coinglass",
                    "data_date": data_date,
                    "fetched_at": fetched,
                }
            else:
                results[key] = None
        except Exception as e:
            print(f"[WARN] coinglass {symbol} OI fetch failed: {e}", file=sys.stderr)
            results[key] = None

    return results


def collect_coinglass_dat():
    """Fetch DAT (Digital Asset Total) weekly net inflow from Coinglass."""
    now = now_kst()
    fetched = now.isoformat()
    try:
        url = "https://open-api.coinglass.com/public/v2/fund-flow?time_type=w"
        data = fetch_json(url)
        net_flow = None
        data_date = now.strftime("%Y-%m-%d")

        if isinstance(data, dict) and data.get("success"):
            d = data.get("data", [])
            if d and isinstance(d, list):
                for item in d:
                    if isinstance(item, dict):
                        # Look for total/net inflow
                        for k in ["netInflow", "totalNetInflow", "changeUsd"]:
                            if k in item:
                                net_flow = float(item[k])
                                break
                        if net_flow is not None:
                            break
        elif isinstance(data, dict):
            d = data.get("data", {})
            if isinstance(d, dict):
                for k in ["netInflow", "totalNetInflow"]:
                    if k in d:
                        net_flow = float(d[k])
                        break

        if net_flow is not None:
            return {
                "value": fmt_money(net_flow),
                "source": "coinglass",
                "data_date": data_date,
                "fetched_at": fetched,
            }
        return None
    except Exception as e:
        print(f"[WARN] coinglass DAT fetch failed: {e}", file=sys.stderr)
        return None


def collect_cb_premium():
    """Load CB premium from cb_premium_input.json."""
    now = now_kst()
    fetched = now.isoformat()
    try:
        if not os.path.exists(CB_INPUT_FILE):
            print(f"[WARN] CB input file not found: {CB_INPUT_FILE}", file=sys.stderr)
            return None
        with open(CB_INPUT_FILE, "r") as f:
            data = json.load(f)
        # Try various keys
        val = data.get("cb_premium") or data.get("value") or data.get("Coinbase_Premium")
        data_date = data.get("date", now.strftime("%Y-%m-%d"))
        if val is not None:
            # Ensure it has % sign format
            v = str(val)
            if "%" not in v:
                v = v + "%"
            if not v.startswith(("+", "-")):
                v = "+" + v
            return {
                "value": v,
                "source": "starchild",
                "data_date": data_date,
                "fetched_at": fetched,
            }
        return None
    except Exception as e:
        print(f"[WARN] CB premium load failed: {e}", file=sys.stderr)
        return None


def validate_sources(sources, today_str):
    """Validate data dates across sources."""
    stale = []
    failed = []
    dates = set()

    for key, src in sources.items():
        if src is None:
            failed.append(key)
            continue
        dd = src.get("data_date", "")
        dates.add(dd)
        # ETF data from previous US business day is expected (T+1)
        # So we accept today or yesterday
        today = datetime.strptime(today_str, "%Y-%m-%d").date()
        src_date = datetime.strptime(dd, "%Y-%m-%d").date()
        if src_date < today - timedelta(days=3):  # Allow up to 3 days stale for long weekends
            stale.append(key)

    if failed:
        status = "partial"
    elif stale:
        status = "stale"
    elif len(dates) <= 2:  # today + yesterday for ETF is fine
        status = "clean"
    else:
        status = "mixed"

    return {
        "all_same_period": len(dates) <= 2,
        "stale_sources": stale,
        "failed_sources": failed,
        "status": status,
    }


def atomic_write_json(data, path):
    """Write JSON atomically via temp file + rename."""
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp) if os.path.exists(tmp) else None
        raise


def main():
    now = now_kst()
    today = now.strftime("%Y-%m-%d")
    print(f"[INFO] Starting daily data collection for {today}")

    # Collect all sources
    sources = {}

    print("[INFO] Fetching SoSoValue ETF data...")
    sosovalue = collect_sosovalue_etf()
    sources.update(sosovalue)

    print("[INFO] Fetching Coinglass OI data...")
    coinglass_oi = collect_coinglass_oi()
    sources.update(coinglass_oi)

    print("[INFO] Fetching Coinglass DAT data...")
    sources["DAT"] = collect_coinglass_dat()

    print("[INFO] Loading CB premium...")
    sources["CB_PREM"] = collect_cb_premium()

    # Build validation
    validation = validate_sources(sources, today)

    # Build output with backward-compatible top-level keys
    output = {
        "date": today,
        "collected_at": now.isoformat(),
    }

    # Backward-compatible flat keys
    btc_etf = sources.get("BTC_ETF")
    eth_etf = sources.get("ETH_ETF")
    btc_oi = sources.get("BTC_OI")
    eth_oi = sources.get("ETH_OI")
    dat = sources.get("DAT")
    cb = sources.get("CB_PREM")

    output["BTC_ETF"] = btc_etf["value"] if btc_etf else "N/A"
    output["ETH_ETF"] = eth_etf["value"] if eth_etf else "N/A"
    output["BTC_OI_24h"] = btc_oi["value"] if btc_oi else "N/A"
    output["ETH_OI_24h"] = eth_oi["value"] if eth_oi else "N/A"
    output["DAT_WEEKLY_NET_INFLOW"] = dat["value"] if dat else "N/A"
    output["Coinbase_Premium"] = cb["value"] if cb else "N/A"

    output["sources"] = {k: v for k, v in sources.items()}
    output["validation"] = validation

    # Atomic write
    try:
        atomic_write_json(output, OUTPUT_FILE)
        print(f"[INFO] Successfully wrote {OUTPUT_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print(f"[INFO] Validation: {validation['status']}")
    if validation["stale_sources"]:
        print(f"[WARN] Stale sources: {validation['stale_sources']}")
    if validation.get("failed_sources"):
        print(f"[WARN] Failed sources: {validation['failed_sources']}")

    # Print collected values
    for key, val in output.items():
        if key in ("sources", "validation", "date", "collected_at"):
            continue
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
