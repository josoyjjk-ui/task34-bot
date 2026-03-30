import sqlite3, subprocess, httpx, asyncio, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('/Users/fireant/.openclaw/workspace/bots/referral-bot/winner_notify.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
MSG = """🎉 축하합니다! 당신은 빌리언즈 친구초대 이벤트 적격자입니다!

빌리언즈 친구초대 이벤트가 모두 종료되었습니다.

📅 다음주 월요일(3/24) 오후 4시~8시 사이에
@Couponybot 에서 상품을 클레임하세요!

⚠️ 오타 등 정보 오류 시 클레임이 제한될 수 있습니다."""

def get_token():
    r = subprocess.run(['security','find-generic-password','-a','referral-bot','-s','telegram-bot-token','-w'], capture_output=True, text=True)
    return r.stdout.strip()

async def run():
    token = get_token()
    base = f"https://api.telegram.org/bot{token}"
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT user_id FROM user_info WHERE agreed=1").fetchall()
    conn.close()
    total = len(users)
    success = failed = blocked = 0
    logger.info(f"대상: {total}명")
    async with httpx.AsyncClient(timeout=30) as client:
        for i, row in enumerate(users, 1):
            uid = row['user_id']
            try:
                r = await client.post(f"{base}/sendMessage", json={"chat_id": uid, "text": MSG})
                d = r.json()
                if d.get("ok"):
                    success += 1
                else:
                    err = d.get("description","")
                    if any(x in err for x in ["blocked","deactivated","not found","chat not found"]):
                        blocked += 1
                    else:
                        failed += 1
                        logger.warning(f"FAIL {uid}: {err}")
            except Exception as e:
                failed += 1
                logger.error(f"ERROR {uid}: {e}")
            if i % 100 == 0:
                logger.info(f"진행 {i}/{total} | 성공:{success} 차단:{blocked} 실패:{failed}")
            await asyncio.sleep(0.05)
    result = f"총:{total} | 성공:{success} | 차단:{blocked} | 실패:{failed}"
    logger.info(f"=== 완료 === {result}")
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/winner_result.txt','w') as f:
        f.write(result)

asyncio.run(run())
