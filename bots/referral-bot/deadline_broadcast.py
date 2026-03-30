import sqlite3, subprocess, httpx, asyncio, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('/Users/fireant/.openclaw/workspace/bots/referral-bot/deadline_broadcast.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
MSG = "⏰ 당첨자 정보 수집이 1시간 후 마감됩니다!\n아직 정보를 제출하지 않으셨다면 지금 바로 /inform 을 입력해 제출해 주세요."

def get_token():
    r = subprocess.run(['security','find-generic-password','-a','referral-bot','-s','telegram-bot-token','-w'], capture_output=True, text=True)
    return r.stdout.strip()

async def send_blast(client, base, users, round_num):
    success = failed = blocked = 0
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
                    logger.warning(f"R{round_num} FAIL {uid}: {err}")
        except Exception as e:
            failed += 1
            logger.error(f"R{round_num} ERROR {uid}: {e}")
        if i % 200 == 0:
            logger.info(f"R{round_num} 진행 {i}/{len(users)} | 성공:{success} 차단:{blocked} 실패:{failed}")
        await asyncio.sleep(0.05)
    logger.info(f"R{round_num} 완료 | 성공:{success} 차단:{blocked} 실패:{failed}")
    return success, blocked, failed

async def run():
    token = get_token()
    base = f"https://api.telegram.org/bot{token}"
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    logger.info(f"대상: {len(users)}명")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # 1차 발송
        s1, b1, f1 = await send_blast(client, base, users, 1)
        logger.info("30초 대기 후 2차 발송...")
        await asyncio.sleep(30)
        # 2차 발송
        s2, b2, f2 = await send_blast(client, base, users, 2)
    
    result = f"1차: 성공{s1}/차단{b1}/실패{f1} | 2차: 성공{s2}/차단{b2}/실패{f2}"
    logger.info(f"=== 전체 완료 === {result}")
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/deadline_result.txt','w') as f:
        f.write(result)
    print(f"FINAL_RESULT:{result}")

asyncio.run(run())
