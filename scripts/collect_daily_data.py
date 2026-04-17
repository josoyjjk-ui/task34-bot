#!/usr/bin/env python3
"""
일일시황 데이터 수집 스크립트 (v2 — 경량화)

cb_premium_input.json에서 전체 데이터를 로드하고,
날짜 교차 검증 + 원자적 파일 쓰기로 데이터 섞임을 원천 차단한다.

입력: cb_premium_input.json (참모 크론이 수집)
출력: daily-report-data.json (하류 크론이 소비)
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(WORKSPACE, "daily-report-data.json")
CB_INPUT_FILE = os.path.join(WORKSPACE, "cb_premium_input.json")

# cb_premium_input.json 키 → daily-report-data.json 키 매핑
FIELD_MAP = {
    "btc_etf":    "BTC_ETF",
    "eth_etf":    "ETH_ETF",
    "btc_oi_24h": "BTC_OI_24h",
    "eth_oi_24h": "ETH_OI_24h",
    "dat_now":    "DAT_WEEKLY_NET_INFLOW",
    "cb_premium": "Coinbase_Premium",
}

# 소스별 출처 태깅
SOURCE_MAP = {
    "BTC_ETF":              "sosovalue",
    "ETH_ETF":              "sosovalue",
    "BTC_OI_24h":           "coinglass",
    "ETH_OI_24h":           "coinglass",
    "DAT_WEEKLY_NET_INFLOW": "coinglass",
    "Coinbase_Premium":     "starchild",
}


def now_kst():
    return datetime.now(KST)


def validate_date(data_date_str, today, max_age_days=3):
    """데이터 날짜가 허용 범위 이내인지 확인. 기본 3일 (T-1 + 주말 마진)."""
    try:
        data_date = datetime.strptime(data_date_str, "%Y-%m-%d").date()
        delta = (today - data_date).days
        return 0 <= delta <= max_age_days
    except (ValueError, TypeError):
        return False


def field_as_of(raw, src_key, fallback_date):
    """필드별 as_of 날짜 추출. cb_premium_input.json의 `{key}_as_of`
    필드가 있으면 우선 사용, 없으면 top-level date로 폴백."""
    per_field = raw.get(f"{src_key}_as_of")
    if per_field:
        # ISO datetime이면 date 부분만 추출
        return str(per_field)[:10]
    return fallback_date


def atomic_write_json(data, path):
    """JSON을 원자적으로 쓴다 (tmp → rename)."""
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main():
    now = now_kst()
    today = now.date()
    today_str = today.strftime("%Y-%m-%d")
    fetched_at = now.isoformat()

    print(f"[INFO] Starting daily data collection for {today_str}")

    # 1. cb_premium_input.json 로드
    if not os.path.exists(CB_INPUT_FILE):
        print(f"[ERROR] Input file not found: {CB_INPUT_FILE}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(CB_INPUT_FILE, "r") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read input: {e}", file=sys.stderr)
        sys.exit(1)

    data_date = raw.get("date", "unknown")
    print(f"[INFO] Input data date: {data_date}")

    # 2. 날짜 검증
    date_valid = validate_date(data_date, today)
    if not date_valid:
        print(f"[WARN] Data date {data_date} is stale (>5 days from {today_str})", file=sys.stderr)

    # 3. 필드 매핑 + 소스 메타데이터 생성 (per-field as_of 추적)
    sources = {}
    failed = []
    stale_sources = []
    unknown_staleness = []
    flat = {}

    for src_key, dst_key in FIELD_MAP.items():
        val = raw.get(src_key)
        if val is not None and val != "":
            field_date = field_as_of(raw, src_key, data_date)
            field_fresh = validate_date(field_date, today, max_age_days=3)
            # ETF/DAT 필드는 T-1 기준이므로 2일 허용. 나머지는 1일(T-0)
            if src_key in ("btc_etf", "eth_etf", "dat_now"):
                field_fresh = validate_date(field_date, today, max_age_days=2)
            flat[dst_key] = str(val)
            sources[dst_key] = {
                "value": str(val),
                "source": SOURCE_MAP.get(dst_key, "unknown"),
                "data_date": field_date,
                "fetched_at": fetched_at,
                "fresh": field_fresh,
            }
            if not field_fresh:
                stale_sources.append(dst_key)
                print(f"[WARN] {dst_key} stale: data_date={field_date} today={today_str}", file=sys.stderr)
            # ETF/DAT는 반드시 per-field as_of가 있어야 함 (없으면 unknown staleness)
            if src_key in ("btc_etf", "eth_etf", "dat_now") and not raw.get(f"{src_key}_as_of"):
                unknown_staleness.append(dst_key)
                print(f"[WARN] {dst_key} has no per-field as_of — staleness UNKNOWN", file=sys.stderr)
        else:
            flat[dst_key] = "N/A"
            sources[dst_key] = None
            failed.append(dst_key)

    # 4. Validation 결정
    if failed:
        status = "partial"
    elif unknown_staleness:
        status = "unknown_staleness"  # ETF/DAT per-field 메타 누락 — 사실상 stale 취급
    elif stale_sources:
        status = "stale"
    elif not date_valid:
        status = "stale"
    else:
        status = "clean"

    validation = {
        "all_same_period": len(set(
            s["data_date"] for s in sources.values() if s is not None
        )) <= 1,
        "stale_sources": stale_sources,
        "unknown_staleness": unknown_staleness,
        "failed_sources": failed,
        "status": status,
    }

    # 5. partial/stale/unknown_staleness 시 기존 파일 보존 (발행 차단)
    if status in ("partial", "stale", "unknown_staleness") and os.path.exists(OUTPUT_FILE):
        print(f"[WARN] Status is '{status}' — preserving existing output file")
        print(f"[WARN] Failed: {failed}" if failed else f"[WARN] Stale data: {data_date}")
        # 기존 파일은 그대로 두고, 검증 결과만 출력
        print(f"[INFO] Validation: {json.dumps(validation, ensure_ascii=False)}")
        sys.exit(0)

    # 6. 출력 JSON 조립
    output = {
        "date": today_str,
        "collected_at": fetched_at,
    }
    output.update(flat)  # 하위호환 플랫 키
    output["sources"] = sources
    output["validation"] = validation

    # 7. 원자적 쓰기
    try:
        atomic_write_json(output, OUTPUT_FILE)
        print(f"[INFO] Successfully wrote {OUTPUT_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
        sys.exit(1)

    # 8. 결과 요약
    print(f"[INFO] Validation: {status}")
    for key, val in flat.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
