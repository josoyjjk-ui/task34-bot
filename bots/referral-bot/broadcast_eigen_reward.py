#!/usr/bin/env python3
"""Broadcast Eigen Cloud /reward notice to all referral bot users."""
import sqlite3
import time
import requests
import subprocess
import sys

DB_PATH = "/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db"
RESULT_PATH = "/Users/fireant/.openclaw/workspace/bots/referral-bot/broadcast_eigen_reward.txt"
DELAY = 0.05

SKIP = 100
PREV_SUCCESS = 96
PREV_BLOCKED = 4
PREV_FAILED = 0

def get_token():
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "referral-bot",
         "-s", "telegram-bot-token", "-w"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

MESSAGE = """⚡️ Eigen Cloud 지급이 완료되었습니다!

친구초대 이벤트 참여자 중 빗썸 거래소로 Eigen 코인을 아직 못 받으신 분들은 아래 방법으로 신청해주세요.

📌 신청 방법
봇에게 /reward 입력 → 빗썸 Eigen 지갑주소 입력

⚠️ 오늘 오후 1시까지만 접수합니다. 이후에는 신청이 불가하니 서둘러주세요!
이번이 찐찐찐막입니다 🙏"""

def send_message(chat_id, text, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return "success"
        err = data.get("description", "")
        if any(k in err.lower() for k in ["blocked","deactivated","chat not found","forbidden"]):
            return "blocked"
        return f"fail:{err}"
    except Exception as e:
        return f"fail:{e}"

def main():
    token = get_token()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    remaining = rows[SKIP:]
    success = PREV_SUCCESS
    blocked = PREV_BLOCKED
    failed = PREV_FAILED

    print(f"[재개] {SKIP+1}~{total} ({len(remaining)}명)")
    sys.stdout.flush()

    for i, (user_id,) in enumerate(remaining, 1):
        result = send_message(user_id, MESSAGE, token)
        if result == "success":
            success += 1
        elif result == "blocked":
            blocked += 1
        else:
            failed += 1
            if failed <= 10:
                print(f"  FAIL uid={user_id}: {result}")

        overall = SKIP + i
        if overall % 200 == 0:
            print(f"  [{overall}/{total}] 성공:{success} 차단:{blocked} 실패:{failed}")
            sys.stdout.flush()

        time.sleep(DELAY)

    summary = f"완료 — 총 {total}명 | 성공 {success} | 차단 {blocked} | 실패 {failed}"
    print(f"\n{summary}")
    with open(RESULT_PATH, "w") as f:
        f.write(summary + "\n")

if __name__ == "__main__":
    main()
