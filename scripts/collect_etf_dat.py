#!/usr/bin/env python3
"""
Farside BTC/ETH ETF + CoinShares DAT auto-collector.

Sources:
  - Farside BTC ETF:  https://farside.co.uk/btc/   (daily net flow, $M)
  - Farside ETH ETF:  https://farside.co.uk/eth/   (daily net flow, $M)
  - CoinShares DAT:   https://coinshares.com/research/digital-asset-fund-flows-weekly-report
                      (weekly net inflow, total across all assets)

Writes into cb_premium_input.json alongside CB Premium data:
  btc_etf, btc_etf_as_of
  eth_etf, eth_etf_as_of
  dat_now, dat_now_as_of

Design notes:
  - Pure stdlib: urllib + html.parser (no beautifulsoup needed)
  - Each source has independent try/except → partial success is acceptable
  - Exit 0 when at least one source succeeds, Exit 1 when all fail
  - ALL writes are atomic (tmp file + os.replace)
  - Preserves all other existing fields (cb_premium, OI, etc.)
"""

import json
import os
import re
import sys
import tempfile
import datetime
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

WORKSPACE = "/Users/fireant/.openclaw/workspace"
OUTPUT = os.path.join(WORKSPACE, "cb_premium_input.json")
KST = datetime.timezone(datetime.timedelta(hours=9))

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605 Fireant-Scraper/1.0"

# -- HTTP ---------------------------------------------------------------------


def http_get(url, timeout=20):
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
    })
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


# -- Farside parser ------------------------------------------------------------


class FarsideTableParser(HTMLParser):
    """Extracts the last data row from a Farside ETF table.

    Farside's ETF tables have:
      row 0: ticker headers (IBIT, FBTC, ...)
      row 1: blank/name row
      rows 2..N-2: daily data (first col = date, last col = Total)
      last row: "Total" summary
    We want the last daily row — the most recent date's Total column.
    """

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.in_td = False
        self.current_row = []
        self.current_cell = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif self.in_tr and tag in ("td", "th"):
            self.in_td = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag in ("td", "th") and self.in_td:
            self.in_td = False
            cell_text = "".join(self.current_cell).strip()
            self.current_row.append(cell_text)

    def handle_data(self, data):
        if self.in_td:
            self.current_cell.append(data)


def _extract_total(row):
    """Given a daily row, return float total or None. Handles "-", "(54.3)", "1,234.5"."""
    for cell in reversed(row):
        cleaned = cell.replace(",", "").strip()
        if not cleaned or cleaned == "-":
            continue
        if re.match(r"^\(?-?\d+(\.\d+)?\)?$", cleaned):
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            try:
                return float(cleaned)
            except ValueError:
                continue
    return None


def parse_farside(html):
    """Return ((iso_date, total_m, raw_row), None) or (None, err_msg).

    Strategy: walk daily rows in forward order, keep the last one whose
    Total is a non-zero number. Skips today's in-progress row (often "-"
    or all zeros) and picks the previous T-1 day.
    """
    p = FarsideTableParser()
    try:
        p.feed(html)
    except Exception as e:
        return None, f"html parse error: {e}"

    if not p.rows:
        return None, "no rows found"

    date_row_re = re.compile(r"^\s*\d{1,2}\s+\w{3,}\s+\d{4}\s*$")
    daily_rows = [r for r in p.rows if r and date_row_re.match(r[0])]
    if not daily_rows:
        return None, "no date rows matched"

    # Pick the last row that has a non-zero numeric total.
    chosen = None
    for row in reversed(daily_rows):
        tot = _extract_total(row)
        if tot is None:
            continue
        # Allow zero only if it's the only row (edge case), else prefer non-zero
        chosen = (row, tot)
        if tot != 0:
            break
    if chosen is None:
        return None, f"no daily row with numeric total ({len(daily_rows)} date rows seen)"

    row, total_m = chosen
    date_str = row[0].strip()
    try:
        dt = datetime.datetime.strptime(date_str, "%d %b %Y").date()
        iso = dt.isoformat()
    except ValueError:
        iso = date_str

    return (iso, total_m, row), None


def format_m(val):
    sign = "+" if val >= 0 else "-"
    return f"{sign}$ {abs(val):.2f}M"


# -- CoinShares DAT ------------------------------------------------------------


def parse_coinshares(html):
    """Best-effort extraction of the weekly net inflow headline from CoinShares.

    Returns (iso_date, total_m, hint) or (None, None, err)
    """
    # Look for patterns like:
    #   "inflows of US$1.1bn"
    #   "net inflows totalling $871m"
    #   "$1.1bn in net inflows"
    patterns = [
        r"inflows?\s+(?:of\s+|totalling\s+|totaling\s+)?US?\$\s*([\d.]+)\s*(bn|m)",
        r"US?\$\s*([\d.]+)\s*(bn|m)\s+(?:in\s+)?(?:net\s+)?inflows?",
        r"net\s+inflows?\s+(?:of\s+)?US?\$\s*([\d.]+)\s*(bn|m)",
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            total_m = value * 1000 if unit == "bn" else value
            # CoinShares weeklies are published Mondays for prior week ending Friday
            today = datetime.datetime.now(KST).date()
            # Find last Friday
            days_back = (today.weekday() - 4) % 7 or 7  # 4=Friday
            last_friday = today - datetime.timedelta(days=days_back)
            return last_friday.isoformat(), total_m, f"matched '{m.group(0)}'"
    return None, None, "no inflow pattern matched in CoinShares HTML"


# -- Main ---------------------------------------------------------------------


def load_existing():
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def atomic_write(data, path):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main():
    now = datetime.datetime.now(KST)
    today = now.date().isoformat()
    existing = load_existing()

    successes = []
    failures = []

    # 1. Farside BTC ETF
    try:
        html = http_get("https://farside.co.uk/btc/")
        result, err = parse_farside(html)
        if err:
            raise ValueError(err)
        iso_date, total_m, _ = result
        existing["btc_etf"] = format_m(total_m)
        existing["btc_etf_as_of"] = iso_date
        print(f"[OK] BTC ETF: {existing['btc_etf']} as_of={iso_date}")
        successes.append("btc_etf")
    except Exception as e:
        msg = f"Farside BTC: {type(e).__name__}: {e}"
        print(f"[ERR] {msg}", file=sys.stderr)
        failures.append(msg)

    # 2. Farside ETH ETF
    try:
        html = http_get("https://farside.co.uk/eth/")
        result, err = parse_farside(html)
        if err:
            raise ValueError(err)
        iso_date, total_m, _ = result
        existing["eth_etf"] = format_m(total_m)
        existing["eth_etf_as_of"] = iso_date
        print(f"[OK] ETH ETF: {existing['eth_etf']} as_of={iso_date}")
        successes.append("eth_etf")
    except Exception as e:
        msg = f"Farside ETH: {type(e).__name__}: {e}"
        print(f"[ERR] {msg}", file=sys.stderr)
        failures.append(msg)

    # 3. CoinShares DAT weekly — try multiple known URL patterns
    COINSHARES_URLS = [
        "https://coinshares.com/research/",
        "https://coinshares.com/research",
        "https://coinshares.com/insights/research/digital-asset-fund-flows",
        "https://blog.coinshares.com/",
    ]
    dat_done = False
    for url in COINSHARES_URLS:
        try:
            html = http_get(url)
            iso_date, total_m, hint = parse_coinshares(html)
            if total_m is None:
                raise ValueError(hint)
            existing["dat_now"] = format_m(total_m)
            existing["dat_now_as_of"] = iso_date
            print(f"[OK] DAT: {existing['dat_now']} as_of={iso_date} (url={url} hint={hint})")
            successes.append("dat_now")
            dat_done = True
            break
        except Exception as e:
            failures.append(f"CoinShares DAT@{url}: {type(e).__name__}: {e}")
            continue
    if not dat_done:
        print(f"[ERR] CoinShares DAT: all {len(COINSHARES_URLS)} URL candidates failed", file=sys.stderr)

    # Meta
    existing.setdefault("date", today)
    existing["etf_dat_last_run"] = now.isoformat()
    if successes:
        existing["etf_dat_last_success"] = now.isoformat()

    atomic_write(existing, OUTPUT)

    print(f"[INFO] saved to {OUTPUT}")
    print(f"[INFO] success={successes} failures_count={len(failures)}")

    if not successes:
        print("[FATAL] all sources failed", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
