import sqlite3, asyncio, re, logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(
    filename='/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_correction.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

BOT_TOKEN = '8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0'

MSG = (
    "📢 *[정정 안내]*\n\n"
    "방금 전 안내 메시지에서 명령어를 잘못 안내드렸습니다. 죄송합니다!\n\n"
    "❌ 잘못된 명령어: `/wallet`\n"
    "✅ *올바른 명령어: `/reward`*\n\n"
    "빗썸 Eigen 입금주소 제출은 `/reward` 를 입력해주세요!\n\n"
    "📅 마감: 오늘 (4월 7일) 오후 11시 59분"
)

async def main():
    # wallet_request2 + wallet_request3 로그에서 발송 성공한 유저 목록 수집
    sent = set()
    for logfile in [
        '/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_request2.log',
        '/Users/fireant/.openclaw/workspace/bots/referral-bot/wallet_request3.log',
    ]:
        try:
            with open(logfile) as f:
                for line in f:
                    m = re.search(r'✅ (\d+)', line)
                    if m:
                        sent.add(int(m.group(1)))
        except:
            pass

    targets = list(sent)
    total = len(targets)
    print(f'정정 발송 대상: {total}명')
    logging.info(f'정정 발송 시작: {total}명')

    bot = Bot(token=BOT_TOKEN)
    success, fail, blocked = 0, 0, 0

    for i, uid in enumerate(targets):
        try:
            await bot.send_message(chat_id=uid, text=MSG, parse_mode='Markdown')
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
