import sqlite3, subprocess, httpx, asyncio, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('/Users/fireant/.openclaw/workspace/bots/referral-bot/last10min.log', mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
MSG = "⏰ 마지막 10분입니다! 당첨자 정보를 아직 제출하지 않으셨다면 지금 바로 /inform 을 입력해 제출해 주세요."
START_INDEX = 1160
TOTAL_ALL = 2415
SUCCESS = 1151
BLOCKED = 9
FAILED = 0

def get_token():
    r = subprocess.run(['security','find-generic-password','-a','referral-bot','-s','telegram-bot-token','-w'], capture_output=True, text=True)
    return r.stdout.strip()

async def run():
    token = get_token()
    base = f"https://api.telegram.org/bot{token}"
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()

    remaining = users[START_INDEX:]
    logger.info(f"재개: {START_INDEX}/{len(users)} 완료 상태에서 시작 | 남은 대상: {len(remaining)}명")

    success = SUCCESS
    failed = FAILED
    blocked = BLOCKED

    async with httpx.AsyncClient(timeout=30) as client:
        for idx, row in enumerate(remaining, START_INDEX + 1):
            uid = row['user_id']
            try:
                r = await client.post(f"{base}/sendMessage", json={"chat_id": uid, "text": MSG})
                d = r.json()
                if d.get("ok"):
                    success += 1
                else:
                    err = d.get("description", "")
                    if any(x in err for x in ["blocked", "deactivated", "not found", "chat not found"]):
                        blocked += 1
                    else:
                        failed += 1
                        logger.warning(f"FAIL {uid}: {err}")
            except Exception as e:
                failed += 1
                logger.error(f"ERROR {uid}: {e}")

            if idx % 200 == 0:
                logger.info(f"진행 {idx}/{TOTAL_ALL} | 성공:{success} 차단:{blocked} 실패:{failed}")
            await asyncio.sleep(0.05)

    result = f"총:{TOTAL_ALL} | 성공:{success} | 차단:{blocked} | 실패:{failed}"
    logger.info(f"=== 완료 === {result}")
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/last10min_result.txt', 'w') as f:
        f.write(result)

asyncio.run(run())
