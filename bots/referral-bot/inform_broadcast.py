import sqlite3, subprocess, httpx, asyncio, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('/Users/fireant/.openclaw/workspace/bots/referral-bot/inform_broadcast.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'

def get_token():
    r = subprocess.run(['security','find-generic-password','-a','referral-bot','-s','telegram-bot-token','-w'], capture_output=True, text=True)
    return r.stdout.strip()

async def run():
    token = get_token()
    logger.info(f"토큰: {token[:20]}...")
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
                r = await client.post(f"{base}/sendMessage", json={
                    "chat_id": uid,
                    "text": "당신은 모든 제출이 완료되었습니다!"
                })
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
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/inform_result.txt','w') as f:
        f.write(result)

asyncio.run(run())
