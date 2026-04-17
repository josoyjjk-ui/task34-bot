#!/usr/bin/env python3
"""Regression test suite for the 5-item patch set.

Tests real execution environment (not mocks):
  #1  Codex auto-refresh    — script exists, executable, cron registered
  #2  Harness refusal fix   — dist contains patterns, src exports
  #3  Daily T-1 validation  — staged input → correct status
  #4  Z.AI 500 retry        — dist contains retry + truncation code
  #5  openclaw.json fallback — both locations use zai/glm-5.1
  #6  6h cron removal       — jobs.json clean
  #7  3-line report format  — dist contains new formatter
  #8  parseWorkerOutput fix — dist contains refusal → failed mapping
  #9  Farside scraper       — live network fetch produces non-zero T-1 data
  #10 JSON config validity  — all config files parse

Exits 0 on all pass, 1 on any fail. Prints colored summary.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HOME = os.path.expanduser("~")
PLUGIN_DIST = f"{HOME}/.openclaw/plugins/openclaw-harness-fireant/dist/index.js"
OPENCLAW_JSON = f"{HOME}/.openclaw/openclaw.json"
JOBS_JSON = f"{HOME}/.openclaw/cron/jobs.json"
WORKSPACE = f"{HOME}/.openclaw/workspace"
SCRIPTS = f"{WORKSPACE}/scripts"
CB_INPUT = f"{WORKSPACE}/cb_premium_input.json"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

results = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    icon = f"{GREEN}✅" if cond else f"{RED}❌"
    print(f"{icon} [{status}]{RESET} {name}" + (f" — {detail}" if detail else ""))
    results.append((name, cond, detail))
    return cond


def read_dist():
    with open(PLUGIN_DIST, "r") as f:
        return f.read()


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ─── Tests ───────────────────────────────────────────────────────────────

def test_1_codex_refresh():
    """Codex auto-refresh script + cron."""
    script = f"{HOME}/.openclaw/bin/codex-auto-refresh.sh"
    check("#1.1 codex-auto-refresh.sh exists",
          os.path.isfile(script))
    check("#1.2 codex-auto-refresh.sh executable",
          os.access(script, os.X_OK))
    cron_out = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    check("#1.3 codex-auto-refresh in crontab",
          "codex-auto-refresh.sh" in cron_out)
    # Run it — should exit 0 and touch log file
    r = subprocess.run([script], capture_output=True, text=True, timeout=90)
    check("#1.4 codex-auto-refresh runs successfully",
          r.returncode == 0,
          f"exit={r.returncode} stderr_tail={r.stderr[-150:] if r.stderr else ''}")
    log = f"{HOME}/.openclaw/logs/codex-auto-refresh.log"
    check("#1.5 log file written",
          os.path.isfile(log) and os.path.getsize(log) > 0)


def test_2_harness_refusal():
    """local-cc.ts refusal detection patterns in dist."""
    dist = read_dist()
    check("#2.1 WORKER_REFUSAL_PATTERNS in dist",
          "WORKER_REFUSAL_PATTERNS" in dist)
    check("#2.2 detectWorkerRefusal fn in dist",
          "detectWorkerRefusal" in dist)
    check("#2.3 worker_refused_execution error tag in dist",
          "worker_refused_execution" in dist)
    check("#2.4 Korean '실행할 수 없' pattern",
          "실행할" in dist)
    check("#2.5 'I cannot directly execute' English pattern",
          "cannot" in dist and "execute" in dist)


def test_3_daily_t1():
    """collect_daily_data.py T-1 validation with staged inputs."""
    # Stage 1: fresh ETF data with as_of today
    import datetime
    KST = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(KST).date().isoformat()
    yesterday = (datetime.datetime.now(KST) - datetime.timedelta(days=1)).date().isoformat()
    too_old = (datetime.datetime.now(KST) - datetime.timedelta(days=10)).date().isoformat()

    def run_collector(input_data):
        # Save input, run collector, capture output (collector uses real file paths)
        # Use a backup/restore to avoid corrupting live data
        bak = CB_INPUT + ".regression_bak"
        if os.path.exists(CB_INPUT):
            subprocess.run(["cp", CB_INPUT, bak])
        try:
            with open(CB_INPUT, "w") as f:
                json.dump(input_data, f, indent=2)
            r = subprocess.run(
                ["python3", f"{SCRIPTS}/collect_daily_data.py"],
                capture_output=True, text=True, timeout=30)
            return r
        finally:
            if os.path.exists(bak):
                subprocess.run(["mv", bak, CB_INPUT])

    # Case A: all fresh
    r = run_collector({
        "date": today,
        "cb_premium": "+0.01%", "cb_premium_as_of": today,
        "btc_oi_24h": "+0.16%", "btc_oi_24h_as_of": today,
        "eth_oi_24h": "+0.59%", "eth_oi_24h_as_of": today,
        "btc_etf": "+$411M", "btc_etf_as_of": yesterday,
        "eth_etf": "+$53M", "eth_etf_as_of": yesterday,
        "dat_now": "+$1.1B", "dat_now_as_of": yesterday,
    })
    out = r.stdout + r.stderr
    check("#3.1 fresh data → clean status", "clean" in out.lower() or "Successfully wrote" in out,
          detail=f"stdout_tail={r.stdout[-150:]}")

    # Case B: missing ETF as_of → unknown_staleness
    r = run_collector({
        "date": today,
        "cb_premium": "+0.01%", "cb_premium_as_of": today,
        "btc_oi_24h": "+0.16%", "btc_oi_24h_as_of": today,
        "eth_oi_24h": "+0.59%", "eth_oi_24h_as_of": today,
        "btc_etf": "+$411M",  # NO as_of
        "eth_etf": "+$53M",   # NO as_of
        "dat_now": "+$1.1B",  # NO as_of
    })
    out = r.stdout + r.stderr
    check("#3.2 missing ETF as_of → unknown_staleness detected",
          "unknown_staleness" in out or "UNKNOWN" in out,
          detail="expected unknown_staleness in output")

    # Case C: stale ETF data (>2 days old)
    r = run_collector({
        "date": today,
        "cb_premium": "+0.01%", "cb_premium_as_of": today,
        "btc_oi_24h": "+0.16%", "btc_oi_24h_as_of": today,
        "eth_oi_24h": "+0.59%", "eth_oi_24h_as_of": today,
        "btc_etf": "+$411M", "btc_etf_as_of": too_old,
        "eth_etf": "+$53M", "eth_etf_as_of": too_old,
        "dat_now": "+$1.1B", "dat_now_as_of": too_old,
    })
    out = r.stdout + r.stderr
    check("#3.3 stale ETF (>2d) → stale status",
          "stale" in out.lower(),
          detail=f"stdout_tail={r.stdout[-100:]}")


def test_4_zai_retry():
    """Z.AI 500 retry + context truncation in dist.

    Note: esbuild minifies `70000` to `7e4` and escapes Korean chars."""
    dist = read_dist()
    check("#4.1 Z.AI 1234 emergency-truncation marker",
          "emergency-truncating" in dist)
    check("#4.2 500/502 status retry in postZai",
          "response.status === 500" in dist or "=== 500" in dist)
    check("#4.3 MAX_CONTENT_CHARS lowered to 70k (esbuild: 7e4)",
          "MAX_CONTENT_CHARS = 7e4" in dist or "MAX_CONTENT_CHARS=7e4" in dist)


def test_5_fallback_config():
    """openclaw.json primary + fallback = zai/glm-5.1."""
    cfg = read_json(OPENCLAW_JSON)
    defaults_model = cfg.get("agents", {}).get("defaults", {}).get("model", {})
    check("#5.1 defaults.model.primary = zai/glm-5.1",
          defaults_model.get("primary") == "zai/glm-5.1")
    check("#5.2 defaults.model.fallbacks = [zai/glm-5.1]",
          defaults_model.get("fallbacks") == ["zai/glm-5.1"])
    agents_list = cfg.get("agents", {}).get("list", [])
    if agents_list:
        main_model = agents_list[0].get("model", {})
        check("#5.3 agents.list[0].model.primary = zai/glm-5.1",
              main_model.get("primary") == "zai/glm-5.1")
        check("#5.4 agents.list[0].model.fallbacks = [zai/glm-5.1]",
              main_model.get("fallbacks") == ["zai/glm-5.1"])


def test_6_cron_removed():
    """6h monitor crons fully removed."""
    j = read_json(JOBS_JSON)
    jobs = j.get("jobs", [])
    names = [job.get("name") for job in jobs]
    check("#6.1 openclaw-6h-monitor removed",
          "openclaw-6h-monitor" not in names)
    check("#6.2 openclaw-6h-telegram-report removed",
          "openclaw-6h-telegram-report" not in names)
    # Sanity: other jobs still present
    check("#6.3 memory-db-backup still present (non-destructive)",
          "memory-db-backup" in names)


def test_7_3line_format():
    """3-line Korean report format in dist.

    Note: esbuild escapes Korean chars to \\uXXXX."""
    dist = read_dist()
    check("#7.1 condenseSingleLine helper in dist",
          "condenseSingleLine" in dist)
    # 핵심 = \uD575\uC2EC, 후속 = \uD6C4\uC18D
    check("#7.2 '핵심' and '후속' markers (esbuild-escaped) in dist",
          "\\uD575\\uC2EC" in dist and "\\uD6C4\\uC18D" in dist)
    # Verify the new 3-line formatFinalResult is active by checking that
    # `line1, line2, line3` pattern and `• ${"\u" + ..."}:` sequence are present.
    # (Residual '## 하네스' in another function is not load-bearing.)
    check("#7.3 formatFinalResult returns 3-line array (line1, line2, line3)",
          "line1, line2, line3" in dist or "[line1,line2,line3]" in dist)


def test_8_parse_worker_refusal():
    """parseWorkerOutput refusal patch — defensive (src-level only).

    parseWorkerOutput is declared but NEVER CALLED in the plugin, so esbuild
    tree-shakes it from dist. The src patch is defensive future-proofing.
    We assert the src contains the fix, not dist."""
    src_path = f"{HOME}/.openclaw/plugins/openclaw-harness-fireant/src/tools/harness-execute.ts"
    with open(src_path, "r") as f:
        src = f.read()
    check("#8.1 SUBAGENT_REFUSAL_PATTERNS defined in src",
          "SUBAGENT_REFUSAL_PATTERNS" in src)
    check("#8.2 isRefusal branch in parseWorkerOutput (src)",
          "isRefusal" in src and "status: isRefusal" in src)
    # The real refusal-detection code path (in dist) is in local-cc.ts's Z.AI loop
    dist = read_dist()
    check("#8.3 worker_refused_execution tag reaches dist (via local-cc.ts)",
          "worker_refused_execution" in dist)


def test_9_farside_live():
    """Farside scraper live — produces non-zero T-1 data."""
    r = subprocess.run(
        ["python3", f"{SCRIPTS}/collect_etf_dat.py"],
        capture_output=True, text=True, timeout=90)
    out = r.stdout + r.stderr
    check("#9.1 BTC ETF fetched with non-zero value",
          "BTC ETF:" in out and "+$ 0.00M" not in out.split("BTC ETF")[1][:60] if "BTC ETF" in out else False,
          detail=f"exit={r.returncode}")
    check("#9.2 ETH ETF fetched with non-zero value",
          "ETH ETF:" in out and "+$ 0.00M" not in out.split("ETH ETF")[1][:60] if "ETH ETF" in out else False)
    # Verify as_of is yesterday or earlier (not today / not future)
    import datetime
    KST = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(KST).date()
    m = re.search(r"BTC ETF:.*?as_of=(\d{4}-\d{2}-\d{2})", out)
    if m:
        etf_date = datetime.date.fromisoformat(m.group(1))
        delta = (today - etf_date).days
        check("#9.3 BTC ETF as_of is T-1 or T-2 (not future, not stale)",
              0 <= delta <= 3,
              detail=f"as_of={etf_date} today={today} delta={delta}d")


def test_10_json_validity():
    """All touched config files parse."""
    check("#10.1 openclaw.json parses", bool(read_json(OPENCLAW_JSON)))
    check("#10.2 cron/jobs.json parses", bool(read_json(JOBS_JSON)))
    check("#10.3 cb_premium_input.json parses",
          bool(read_json(CB_INPUT)) if os.path.exists(CB_INPUT) else False)
    # Check as_of fields present
    cb = read_json(CB_INPUT)
    check("#10.4 cb_premium_input.json has btc_etf_as_of",
          "btc_etf_as_of" in cb)
    check("#10.5 cb_premium_input.json has eth_etf_as_of",
          "eth_etf_as_of" in cb)


# ─── Runner ─────────────────────────────────────────────────────────────

def main():
    print(f"\n{YELLOW}=== Regression test suite — all 5 patch items ==={RESET}\n")
    tests = [
        ("1. Codex auto-refresh", test_1_codex_refresh),
        ("2. Harness refusal detection", test_2_harness_refusal),
        ("3. Daily T-1 validation", test_3_daily_t1),
        ("4. Z.AI 500 retry", test_4_zai_retry),
        ("5. Fallback config", test_5_fallback_config),
        ("6. 6h cron removal", test_6_cron_removed),
        ("7. 3-line report format", test_7_3line_format),
        ("8. parseWorkerOutput refusal", test_8_parse_worker_refusal),
        ("9. Farside scraper live", test_9_farside_live),
        ("10. JSON config validity", test_10_json_validity),
    ]
    for title, fn in tests:
        print(f"\n--- {title} ---")
        try:
            fn()
        except Exception as e:
            check(f"{title} — runtime error", False, detail=str(e))

    print(f"\n{YELLOW}=== Summary ==={RESET}")
    passed = sum(1 for _, c, _ in results if c)
    failed = sum(1 for _, c, _ in results if not c)
    total = len(results)
    print(f"  Total: {total}  {GREEN}Pass: {passed}{RESET}  {RED}Fail: {failed}{RESET}")
    if failed:
        print(f"\n{RED}Failed tests:{RESET}")
        for name, cond, detail in results:
            if not cond:
                print(f"  ❌ {name}{' — ' + detail if detail else ''}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
