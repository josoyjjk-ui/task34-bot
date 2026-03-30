import sqlite3, subprocess, httpx, asyncio, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler('/Users/fireant/.openclaw/workspace/bots/referral-bot/deadline_broadcast2b.log'),
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
MSG = "⏰ 당첨자 정보 수집이 1시간 후 마감됩니다!\n아직 정보를 제출하지 않으셨다면 지금 바로 /inform 을 입력해 제출해 주세요."
START_OFFSET = 400  # 이미 처리된 400명 이후부터

def get_token():
    r = subprocess.run(['security','find-generic-password','-a','referral-bot','-s','telegram-bot-token','-w'], capture_output=True, text=True)
    return r.stdout.strip()

async def run():
    token = get_token()
    base = f"https://api.telegram.org/bot{token}"
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    all_users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    users = all_users[START_OFFSET:]
    total_all = len(all_users)
    total = len(users)
    success = failed = blocked = 0
    logger.info(f"재시작: {START_OFFSET+1}번째부터, 남은 대상: {total}명 (전체 {total_all}명)")
    
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
            if i % 200 == 0:
                logger.info(f"진행 {START_OFFSET+i}/{total_all} | 성공:{success} 차단:{blocked} 실패:{failed}")
            await asyncio.sleep(0.05)
    
    # 1차분(400명) 성공 포함 합산
    total_success = 400 + success  # 1차분 약 398 + 이번
    result = f"총:{total_all} | 성공:{total_success}(1차400+2차{success}) | 차단:{blocked} | 실패:{failed}"
    logger.info(f"=== 완료 === {result}")
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/deadline_result2.txt','w') as f:
        f.write(result)
    
    # 텔레그램 결과 보고용 간략 수치 저장
    with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/deadline_result2_short.txt','w') as f:
        f.write(f"{total_all}|{total_success}|{blocked}|{failed}")

asyncio.run(run())
