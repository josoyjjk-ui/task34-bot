import sqlite3, asyncio, sys
from telegram import Bot
from telegram.error import TelegramError

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'
DB_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
LOG_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/send_reward_notice_rest.log'

MSG = (
    "🪙 *[Eigen Cloud 리워드 안내]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "Eigen Cloud 이벤트 리워드 지급을 위해 *빗썸 거래소의 Eigen 코인 입금 주소*를 수집합니다.\n\n"
    "📌 제출 방법:\n"
    "1️⃣ 빗썸 앱 → 입금 → Eigen 검색\n"
    "2️⃣ 입금 주소 복사\n"
    "3️⃣ 이 봇에서 /reward 입력 후 주소 붙여넣기\n\n"
    "⚠️ 빗썸 거래소 Eigen 입금 주소만 유효합니다.\n"
    "아직 빗썸 계정이 없으신 분은 가입 후 제출해주세요!\n\n"
    "📅 제출 기한은 별도 안내 예정입니다."
)

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 이전에 보낸 636명을 제외한 나머지 봇 등록자 전원
    rows = conn.execute('SELECT DISTINCT user_id FROM users WHERE user_id NOT IN (SELECT user_id FROM user_info WHERE agreed=1)').fetchall()
    conn.close()

    bot = Bot(token=BOT_TOKEN)
    success, fail = 0, 0
    total = len(rows)

    with open(LOG_PATH, 'w') as log:
        log.write(f"시작: 총 {total}명\n")
        log.flush()

        for i, row in enumerate(rows):
            uid = row['user_id']
            try:
                await bot.send_message(chat_id=uid, text=MSG, parse_mode='Markdown')
                success += 1
            except TelegramError as e:
                fail += 1
                log.write(f"FAIL uid={uid}: {e}\n")

            if (i+1) % 30 == 0:
                await asyncio.sleep(1)
                msg = f"진행: {i+1}/{total} (성공:{success} 실패:{fail})\n"
                log.write(msg)
                log.flush()
                print(msg, end='', flush=True)

        final = f"\n완료! 성공:{success} 실패:{fail} 총:{total}\n"
        log.write(final)
        print(final)

if __name__ == '__main__':
    asyncio.run(main())