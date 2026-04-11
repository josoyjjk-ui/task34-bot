import sqlite3, asyncio, time
from telegram import Bot
from telegram.error import TelegramError

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'
DB_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'

MSG = (
    "🪙 *[Eigen Cloud 리워드 안내]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "빗썸 Eigen 지갑주소 제출 마감까지 *3시간 남았습니다.*\n\n"
    "아직 제출하지 않으신 분들은 채팅창에 */reward* 명령어를 입력하신 뒤,\n"
    "안내에 따라 *빗썸 Eigen 지갑주소*를 꼭 제출해주시기 바랍니다.\n\n"
    "기한 내 제출하지 않으면 지급이 지연될 수 있습니다.\n"
    "누락 없이 꼭 부탁드립니다."
)

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT user_id FROM user_info WHERE agreed=1 AND (bithumb_wallet IS NULL OR TRIM(bithumb_wallet)='')").fetchall()
    conn.close()

    bot = Bot(token=BOT_TOKEN)
    success, fail = 0, 0
    total = len(rows)

    for i, row in enumerate(rows):
        uid = row['user_id']
        try:
            await bot.send_message(chat_id=uid, text=MSG, parse_mode='Markdown')
            success += 1
        except TelegramError:
            fail += 1
        
        if (i+1) % 30 == 0:
            await asyncio.sleep(1)
            print(f'진행: {i+1}/{total} (성공:{success} 실패:{fail})')

    print(f'완료! 성공:{success} 실패:{fail} 총:{total}')

asyncio.run(main())
