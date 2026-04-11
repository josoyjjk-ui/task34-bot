import sqlite3, asyncio, logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(
    filename='/Users/fireant/.openclaw/workspace/bots/referral-bot/groupb_broadcast.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'
DB_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'

MSG = (
    "🪙 *[Eigen Cloud 리워드 안내]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "Eigen Cloud 이벤트 리워드 지급을 위해 *빗썸 거래소의 Eigen 코인 입금주소* 제출이 필요합니다.\n\n"
    "✅ 이벤트 참여자이신 경우 아래 방법으로 제출해주세요.\n\n"
    "📌 제출 방법:\n"
    "1️⃣ 이 봇에서 `/reward` 입력\n"
    "2️⃣ 빗썸 앱 → 입금 → Eigen 검색 → 입금주소 복사\n"
    "3️⃣ 복사한 주소를 봇에 붙여넣기\n\n"
    "⚠️ 주의사항:\n"
    "• *빗썸 거래소 Eigen 입금주소*만 유효합니다\n"
    "• 이벤트 미참여자는 제출하셔도 리워드가 지급되지 않습니다\n\n"
    "📅 *제출 마감: 오늘 (4월 7일) 오후 11시 59분*\n\n"
    "마감 이후 미제출 시 리워드 지급이 어려울 수 있으니 꼭 제출해주세요! 🙏"
)

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT user_id FROM users WHERE user_id NOT IN (SELECT user_id FROM user_info WHERE agreed=1)"
    ).fetchall()
    conn.close()

    targets = [r['user_id'] for r in rows]
    total = len(targets)
    print(f'그룹B 발송 대상: {total}명')
    logging.info(f'그룹B 발송 시작: {total}명')

    bot = Bot(token=BOT_TOKEN)
    success, fail, blocked = 0, 0, 0

    for i, uid in enumerate(targets):
        try:
            await bot.send_message(chat_id=uid, text=MSG, parse_mode='Markdown')
            success += 1
            logging.info(f'[{i+1}/{total}] ✅ {uid}')
        except TelegramError as e:
            err = str(e)
            if 'blocked' in err or 'deactivated' in err or 'not found' in err.lower() or 'chat not found' in err.lower() or 'Forbidden' in err:
                blocked += 1
                logging.info(f'[{i+1}/{total}] 🚫 {uid} {err[:50]}')
            else:
                fail += 1
                logging.info(f'[{i+1}/{total}] ❌ {uid} {err[:60]}')

        if (i+1) % 30 == 0:
            await asyncio.sleep(1)
            print(f'진행: {i+1}/{total} (성공:{success} 차단/불가:{blocked} 실패:{fail})')

    print(f'\n완료! 성공:{success} 차단/불가:{blocked} 실패:{fail} 총:{total}')
    logging.info(f'완료 | 성공:{success} 차단/불가:{blocked} 실패:{fail}')

asyncio.run(main())
