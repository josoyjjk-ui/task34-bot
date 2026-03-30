#!/usr/bin/env python3
import sqlite3
import time
import requests
import sys

BOT_TOKEN = "8715030972:AAHkM8zEkiLrkBzp8rIK-LJ4tmXUsct2kyc"
DB_PATH = "/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db"
RESULT_PATH = "/Users/fireant/.openclaw/workspace/bots/referral-bot/broadcast_result.txt"
DELAY = 0.05

# 이미 처리된 수 (1차 실행 결과)
PREV_TOTAL = 500
PREV_SUCCESS = 482
PREV_BLOCKED = 3
PREV_FAILED = 15
SKIP = 500  # 첫 500명 스킵

MESSAGE = """📣 불개미 x Billions 친구초대 보상 수령 안내드립니다. 

보상신청은 22일 까지만 가능하니 꼭 확인하시기 바랍니다. 

[해당 게시글 보고 꼭 신청하세요](https://t.me/fireantcrypto/40261)"""

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return "success"
        else:
            err = data.get("description", "")
            if any(k in err.lower() for k in ["blocked", "bot was blocked", "user is deactivated", "chat not found", "forbidden"]):
                return "blocked"
            return f"fail:{err}"
    except Exception as e:
        return f"fail:{str(e)}"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()

    total_all = len(rows)
    remaining = rows[SKIP:]

    success = PREV_SUCCESS
    blocked = PREV_BLOCKED
    failed = PREV_FAILED

    print(f"[공병] 브로드캐스트 재개 — {SKIP+1}번~{total_all}번 ({len(remaining)}명 남음)")
    sys.stdout.flush()

    for i, (user_id,) in enumerate(remaining, 1):
        result = send_message(user_id, MESSAGE)
        if result == "success":
            success += 1
        elif result == "blocked":
            blocked += 1
        else:
            failed += 1
            print(f"  FAIL uid={user_id}: {result}")

        overall = SKIP + i
        if overall % 100 == 0:
            print(f"  [{overall}/{total_all}] 성공:{success} 차단:{blocked} 실패:{failed}")
            sys.stdout.flush()

        time.sleep(DELAY)

    total = total_all
    summary = f"브로드캐스트 완료 — 총 {total}명 | 성공 {success} | 차단 {blocked} | 실패 {failed}"
    print(f"\n[공병] {summary}")

    with open(RESULT_PATH, "w") as f:
        f.write(summary + "\n")

    print(f"결과 저장: {RESULT_PATH}")
    return total, success, blocked, failed

if __name__ == "__main__":
    main()
