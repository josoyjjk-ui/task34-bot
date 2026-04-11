import sqlite3, asyncio, time, logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(
    filename='/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_request2.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'
DB_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'

MSG = (
    "🪙 *[Eigen Cloud 리워드 안내 — 재공지]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "Eigen Cloud 이벤트 리워드 지급을 위해 *빗썸 거래소의 Eigen 코인 입금 주소* 제출이 필요합니다.\n\n"
    "📌 제출 방법:\n"
    "1️⃣ 빗썸 앱 → 입금 → Eigen 검색\n"
    "2️⃣ 입금 주소 복사\n"
    "3️⃣ 이 봇에서 /wallet 입력 후 주소 붙여넣기\n\n"
    "⚠️ 빗썸 거래소 Eigen 입금 주소만 유효합니다.\n"
    "아직 빗썸 계정이 없으신 분은 가입 후 제출해주세요!\n\n"
    "📅 *제출 마감: 2026년 4월 7일 (오늘) 오후 11시 59분*\n\n"
    "마감 이후 미제출 시 리워드 지급이 어려울 수 있으니 꼭 제출해주세요! 🙏"
)

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT user_id FROM user_info WHERE agreed=1').fetchall()
    conn.close()

    bot = Bot(token=BOT_TOKEN)
    success, fail, blocked = 0, 0, 0
    total = len(rows)
    print(f'총 {total}명에게 발송 시작')
    logging.info(f'발송 시작: {total}명')

    for i, row in enumerate(rows):
        uid = row['user_id']
        try:
            await bot.send_message(chat_id=uid, text=MSG, parse_mode='Markdown')
            success += 1
            logging.info(f'[{i+1}/{total}] ✅ {uid}')
        except TelegramError as e:
            err = str(e)
            if 'blocked' in err or 'deactivated' in err or 'not found' in err.lower():
                blocked += 1
                logging.info(f'[{i+1}/{total}] 🚫 {uid} blocked')
            else:
                fail += 1
                logging.info(f'[{i+1}/{total}] ❌ {uid} {err[:60]}')

        if (i+1) % 30 == 0:
            await asyncio.sleep(1)
            print(f'진행: {i+1}/{total} (성공:{success} 차단:{blocked} 실패:{fail})')

    print(f'\n완료! 성공:{success} 차단:{blocked} 실패:{fail} 총:{total}')
    logging.info(f'완료 | 성공:{success} 차단:{blocked} 실패:{fail}')

asyncio.run(main())
