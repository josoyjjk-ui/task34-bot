import asyncio
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from telegram import Bot
from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError

BOT_TOKEN = "8715030972:AAEaCj5zaNsB6OhwBhXwg6gZ0KM8ibXOpW0"
DB_PATH = "/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db"
QUERY = """
SELECT u.user_id
FROM users u
LEFT JOIN user_info ui ON u.user_id = ui.user_id
WHERE ui.bithumb_wallet IS NULL OR TRIM(ui.bithumb_wallet) = ''
"""
MESSAGE = """빗썸 Eigen 지갑주소 제출 마감까지 *2시간 남았습니다.*

아직 제출하지 않으신 분들은 채팅창에 */reward* 명령어를 입력하신 뒤,
안내에 따라 *빗썸 Eigen 지갑주소*를 꼭 제출해주시기 바랍니다.

마감: *오늘 오후 4시 30분*

기한 내 제출하지 않으면 지급이 지연될 수 있습니다.
마지막 안내입니다. 누락 없이 꼭 부탁드립니다."""


def setup_logger() -> tuple[logging.Logger, Path]:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    log_path = Path(f"/Users/fireant/.openclaw/workspace/bots/referral-bot/send_eigen_ops_{ts}.log")
    logger = logging.getLogger("send_eigen_ops")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, log_path


def load_user_ids() -> list[int]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(QUERY).fetchall()
        return [int(row[0]) for row in rows]
    finally:
        conn.close()


async def send_all() -> int:
    logger, log_path = setup_logger()
    user_ids = load_user_ids()
    total = len(user_ids)
    logger.info(f"발송 시작: {total}명")

    bot = Bot(token=BOT_TOKEN)
    success = 0
    blocked = 0
    gone = 0
    failed = 0

    for idx, user_id in enumerate(user_ids, start=1):
        try:
            await bot.send_message(chat_id=user_id, text=MESSAGE, parse_mode="Markdown")
            success += 1
            logger.info(f"[{idx}/{total}] ✅ {user_id}")
        except RetryAfter as exc:
            wait_s = max(int(exc.retry_after), 1)
            logger.warning(f"[{idx}/{total}] ⏳ rate limit, {wait_s}s 대기 후 재시도: {user_id}")
            await asyncio.sleep(wait_s)
            try:
                await bot.send_message(chat_id=user_id, text=MESSAGE, parse_mode="Markdown")
                success += 1
                logger.info(f"[{idx}/{total}] ✅ {user_id} (재시도 성공)")
            except Forbidden:
                blocked += 1
                logger.warning(f"[{idx}/{total}] 🚫 {user_id} (차단)")
            except TelegramError as exc2:
                detail = str(exc2)
                if "410" in detail or "Gone" in detail:
                    gone += 1
                    logger.warning(f"[{idx}/{total}] 👋 {user_id} (탈퇴/410: {detail})")
                else:
                    failed += 1
                    logger.error(f"[{idx}/{total}] ❌ {user_id} ({detail})")
        except Forbidden:
            blocked += 1
            logger.warning(f"[{idx}/{total}] 🚫 {user_id} (차단)")
        except NetworkError as exc:
            failed += 1
            logger.error(f"[{idx}/{total}] 🌐 {user_id} (네트워크 오류: {exc})")
        except TelegramError as exc:
            detail = str(exc)
            if "410" in detail or "Gone" in detail:
                gone += 1
                logger.warning(f"[{idx}/{total}] 👋 {user_id} (탈퇴/410: {detail})")
            elif "403" in detail or "Forbidden" in detail:
                blocked += 1
                logger.warning(f"[{idx}/{total}] 🚫 {user_id} (차단: {detail})")
            else:
                failed += 1
                logger.error(f"[{idx}/{total}] ❌ {user_id} ({detail})")

        if idx % 30 == 0 and idx < total:
            logger.info(f"진행상황: {idx}/{total}, 성공:{success}, 차단:{blocked}, 탈퇴:{gone}, 실패:{failed}")
            await asyncio.sleep(1)

    logger.info(f"완료 — 성공:{success}, 차단:{blocked}, 탈퇴:{gone}, 실패:{failed}, 총:{total}")
    print(log_path)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(send_all()))
