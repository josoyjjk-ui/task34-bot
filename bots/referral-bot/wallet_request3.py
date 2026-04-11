import sqlite3, asyncio, re, logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(
    filename='/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_request3.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'
DB_PATH = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'

MSG_ELIGIBLE = (
    "🪙 *[Eigen Cloud 리워드 안내 — 마감 임박]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "Eigen Cloud 이벤트 리워드 지급을 위해 *빗썸 거래소의 Eigen 코인 입금 주소* 제출이 필요합니다.\n\n"
    "✅ 확인 결과 리워드 지급 대상자이십니다!\n\n"
    "📌 제출 방법:\n"
    "1️⃣ 빗썸 앱 → 입금 → Eigen 검색\n"
    "2️⃣ 입금 주소 복사\n"
    "3️⃣ 이 봇에서 /wallet 입력 후 주소 붙여넣기\n\n"
    "⚠️ 빗썸 거래소 Eigen 입금 주소만 유효합니다.\n\n"
    "📅 *제출 마감: 2026년 4월 7일 (오늘) 오후 11시 59분*\n\n"
    "마감 이후 미제출 시 리워드 지급이 어려울 수 있으니 꼭 제출해주세요! 🙏"
)

MSG_NOT_ELIGIBLE = (
    "🪙 *[Eigen Cloud 리워드 안내]*\n\n"
    "안녕하세요! 불개미 크립토 친구초대 이벤트봇입니다.\n\n"
    "빗썸 Eigen 입금 주소 수집과 관련하여 안내드립니다.\n\n"
    "⚠️ 확인 결과 이번 Eigen Cloud 친구초대 이벤트 *리워드 지급 대상자가 아닙니다.*\n\n"
    "주소를 제출하셔도 리워드가 지급되지 않으니 참고해주세요.\n\n"
    "문의사항이 있으시면 불개미 크립토 채널로 문의해주세요."
)

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 이미 발송된 목록 (wallet_request2.log)
    sent = set()
    try:
        with open('/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_request2.log') as f:
            for line in f:
                m = re.search(r'✅ (\d+)', line)
                if m:
                    sent.add(int(m.group(1)))
    except:
        pass
    print(f'이미 발송됨: {len(sent)}명 (제외)')

    # 이미 제출 완료자
    submitted = set(
        r['user_id'] for r in conn.execute(
            "SELECT user_id FROM user_info WHERE bithumb_wallet IS NOT NULL AND bithumb_wallet != ''"
        ).fetchall()
    )

    # 적격자 목록 (users 테이블)
    eligible = set(r['user_id'] for r in conn.execute("SELECT user_id FROM users").fetchall())

    # 미제출자 (user_info agreed=1)
    not_submitted = [
        r for r in conn.execute(
            "SELECT user_id FROM user_info WHERE agreed=1 AND (bithumb_wallet IS NULL OR bithumb_wallet = '')"
        ).fetchall()
        if r['user_id'] not in sent and r['user_id'] not in submitted
    ]
    conn.close()

    group_a = [r['user_id'] for r in not_submitted if r['user_id'] in eligible]
    group_c = [r['user_id'] for r in not_submitted if r['user_id'] not in eligible]

    print(f'그룹A(적격+미제출): {len(group_a)}명')
    print(f'그룹C(비적격+미제출): {len(group_c)}명')
    logging.info(f'발송 시작 | A:{len(group_a)} C:{len(group_c)}')

    bot = Bot(token=BOT_TOKEN)
    success, fail, blocked = 0, 0, 0
    total = len(group_a) + len(group_c)

    targets = [(uid, MSG_ELIGIBLE) for uid in group_a] + [(uid, MSG_NOT_ELIGIBLE) for uid in group_c]

    for i, (uid, msg) in enumerate(targets):
        try:
            await bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown')
            success += 1
            logging.info(f'[{i+1}/{total}] ✅ {uid}')
        except TelegramError as e:
            err = str(e)
            if 'blocked' in err or 'deactivated' in err or 'not found' in err.lower():
                blocked += 1
                logging.info(f'[{i+1}/{total}] 🚫 {uid}')
            else:
                fail += 1
                logging.info(f'[{i+1}/{total}] ❌ {uid} {err[:60]}')

        if (i+1) % 30 == 0:
            await asyncio.sleep(1)
            print(f'진행: {i+1}/{total} (성공:{success} 차단:{blocked} 실패:{fail})')

    print(f'\n완료! 성공:{success} 차단:{blocked} 실패:{fail} 총:{total}')
    logging.info(f'완료 | 성공:{success} 차단:{blocked} 실패:{fail}')

asyncio.run(main())
