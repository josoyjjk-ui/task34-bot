#!/usr/bin/env python3
"""
Referral Bot - 텔레그램 채널 친구초대 이벤트 봇
Python 3 + python-telegram-bot v20+ (async)
이벤트 격리 지원 (events 테이블 기반)
"""

import os
import csv
import io
import json
import logging
import sqlite3
import subprocess
import threading
from datetime import datetime
from contextlib import contextmanager

# Google Sheets 연동
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build as gbuild
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

GSHEETS_TOKEN   = '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json'
GSHEETS_SERVICE_ACCOUNT = '/Users/fireant/.openclaw/workspace/secrets/fireant-workspace-sa.json'
GSHEETS_SCOPES  = ['https://www.googleapis.com/auth/spreadsheets']
GSHEETS_SHEET_ID = '1prtoKycManbOj-HoMnzZ68kl6VEEm3h5vvvTUzK6QHs'
GSHEETS_RANGE    = 'Sheet1!A:J'

def build_sheets_service():
    """가능하면 서비스계정 우선, 실패 시 OAuth 토큰 사용"""
    last_error = None

    if GSHEETS_AVAILABLE and os.path.exists(GSHEETS_SERVICE_ACCOUNT):
        try:
            creds = service_account.Credentials.from_service_account_file(
                GSHEETS_SERVICE_ACCOUNT, scopes=GSHEETS_SCOPES
            )
            return gbuild('sheets', 'v4', credentials=creds, cache_discovery=False)
        except Exception as e:
            last_error = e

    try:
        creds = Credentials.from_authorized_user_file(GSHEETS_TOKEN, GSHEETS_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return gbuild('sheets', 'v4', credentials=creds, cache_discovery=False)
    except Exception as e:
        if last_error:
            logging.getLogger(__name__).error(f"Sheets 서비스계정/OAuth 모두 실패: SA={last_error}, OAuth={e}")
        raise


def get_sheets_id(event_id: int = None) -> str:
    """이벤트별 sheets_id 로드. 없으면 기본값 사용."""
    if event_id:
        with get_db() as conn:
            row = conn.execute("SELECT sheets_id FROM events WHERE id=?", (event_id,)).fetchone()
            if row and row["sheets_id"]:
                return row["sheets_id"]
    return GSHEETS_SHEET_ID


def append_to_sheet(row: list, event_id: int = None):
    """Google Sheets에 행 추가 (비동기 스레드로 실행)"""
    if not GSHEETS_AVAILABLE:
        return
    sheet_id = get_sheets_id(event_id)

    def _write():
        try:
            service = build_sheets_service()
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=GSHEETS_RANGE,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()
        except Exception as e:
            logging.getLogger(__name__).error(f"Sheets 기록 실패: {e}")
    threading.Thread(target=_write, daemon=True).start()

def delete_from_sheet(user_id: int, event_id: int = None):
    """Sheets에서 user_id가 일치하는 행 삭제 (B열 = user_id)"""
    if not GSHEETS_AVAILABLE:
        return
    sheet_id = get_sheets_id(event_id)
    try:
        service = build_sheets_service()
        sheet_name = GSHEETS_RANGE.split('!')[0]
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!A:B'
        ).execute()
        values = result.get('values', [])
        rows_to_delete = []
        for i, row in enumerate(values):
            if len(row) > 1 and row[1] == str(user_id):
                rows_to_delete.append(i)
        for row_idx in reversed(rows_to_delete):
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    'requests': [{
                        'deleteDimension': {
                            'range': {
                                'sheetId': 0,
                                'dimension': 'ROWS',
                                'startIndex': row_idx,
                                'endIndex': row_idx + 1
                            }
                        }
                    }]
                }
            ).execute()
        logger.info(f"Sheets 삭제 완료: user_id={user_id}, 삭제 행 수={len(rows_to_delete)}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Sheets 삭제 예외: {e}")


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ── 설정 ────────────────────────────────────────────────────────────────────
def get_token() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "referral-bot",
         "-s", "telegram-bot-token", "-w"],
        capture_output=True, text=True
    )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Keychain에서 봇 토큰을 가져올 수 없습니다.")
    return token

ADMIN_ID = 477743685
DB_PATH = os.path.join(os.path.dirname(__file__), "referral.db")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "bot.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ConversationHandler 상태
WAITING_REFERRER = 1
WAITING_RESET_CONFIRM = 2

# /inform 상태값
INF_EMAIL    = 10
INF_TG       = 11
INF_PHONE    = 12
INF_AGREE    = 13
INF_REALNAME = 14
INF_WALLET   = 15
INF_EDIT_CONFIRM = 20
WALLET_INPUT = 21
REWARD_INPUT = 22

# ── DB ───────────────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_active_event_id() -> int:
    """현재 활성 이벤트 ID 반환. 없으면 1."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM events WHERE is_active=1 ORDER BY id DESC LIMIT 1").fetchone()
    return row["id"] if row else 1


def get_active_event():
    """현재 활성 이벤트 전체 정보 반환."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM events WHERE is_active=1 ORDER BY id DESC LIMIT 1").fetchone()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                start_date  TEXT,
                end_date    TEXT,
                channels    TEXT,
                welcome_msg TEXT,
                sheets_id   TEXT,
                is_active   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS channels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id  INTEGER NOT NULL,
                channel_name TEXT,
                event_id    INTEGER REFERENCES events(id) DEFAULT 1,
                added_at    TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(channel_id, event_id)
            );

            -- event_period 레거시 테이블 제거됨 — events 테이블로 대체
        """)

        # users 테이블 — 이미 마이그레이션된 스키마면 건드리지 않음
        users_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if not users_exists:
            conn.executescript("""
                CREATE TABLE users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    event_id    INTEGER NOT NULL DEFAULT 1 REFERENCES events(id),
                    username    TEXT,
                    first_name  TEXT,
                    points      INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    ever_registered INTEGER DEFAULT 0,
                    registered_at TEXT DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(user_id, event_id)
                );
            """)

        # user_info 테이블
        ui_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_info'").fetchone()
        if not ui_exists:
            conn.executescript("""
                CREATE TABLE user_info (
                    user_id     INTEGER NOT NULL,
                    event_id    INTEGER NOT NULL DEFAULT 1 REFERENCES events(id),
                    email       TEXT,
                    telegram_id TEXT,
                    phone       TEXT,
                    agreed      INTEGER DEFAULT 0,
                    submitted_at TEXT DEFAULT (datetime('now', 'localtime')),
                    real_name   TEXT,
                    wallet      TEXT,
                    bithumb_wallet TEXT,
                    PRIMARY KEY (user_id, event_id)
                );
            """)

    logger.info("DB 초기화 완료: %s", DB_PATH)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────
def is_event_active() -> bool:
    event = get_active_event()
    if not event:
        return True
    if event["start_date"] is None and event["end_date"] is None:
        return True
    now = datetime.now().strftime("%Y-%m-%d")
    start = event["start_date"] or "0000-00-00"
    end   = event["end_date"]   or "9999-12-31"
    return start <= now <= end


def get_user(user_id: int, event_id: int = None):
    if event_id is None:
        event_id = get_active_event_id()
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()


def register_user(user_id: int, username: str, first_name: str) -> bool:
    """새 유저 등록. 이미 해당 이벤트에 등록됐으면 False."""
    event_id = get_active_event_id()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, ever_registered FROM users WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
        if existing:
            if existing["ever_registered"] == 1:
                return False
            conn.execute(
                "UPDATE users SET username=?, first_name=?, points=10, ever_registered=1 WHERE id=?",
                (username, first_name, existing["id"])
            )
            return True
        conn.execute(
            "INSERT INTO users (user_id, event_id, username, first_name, points, ever_registered) VALUES (?,?,?,?,10,1)",
            (user_id, event_id, username, first_name)
        )
    return True


def set_referrer(user_id: int, referrer_input: str) -> tuple:
    """초대자 설정. 같은 이벤트 내에서만."""
    event_id = get_active_event_id()
    username_clean = referrer_input.lstrip("@").strip().lower()
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, referrer_id FROM users WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
        if not user:
            return False, "먼저 /start로 등록해주세요.", 0
        if user["referrer_id"] is not None:
            return False, "이미 초대자가 등록되어 있습니다.", 0
        referrer = conn.execute(
            "SELECT user_id, first_name, points FROM users WHERE LOWER(username)=? AND event_id=?",
            (username_clean, event_id)
        ).fetchone()
        if not referrer:
            return False, f"@{username_clean} 유저를 찾을 수 없습니다.\n상대방도 먼저 봇에서 /start 를 눌러야 합니다.", 0
        if referrer["user_id"] == user_id:
            return False, "자기 자신을 초대자로 등록할 수 없습니다.", 0
        conn.execute("UPDATE users SET referrer_id=? WHERE id=?", (referrer["user_id"], user["id"]))
        conn.execute("UPDATE users SET points = points + 10 WHERE user_id=? AND event_id=?", (referrer["user_id"], event_id))
        conn.execute("UPDATE users SET points = points + 10 WHERE user_id=? AND event_id=?", (user_id, event_id))
        new_points = referrer["points"] + 10
    return True, referrer["first_name"], referrer["user_id"], new_points


def get_leaderboard(limit: int = 10, event_id: int = None):
    if event_id is None:
        event_id = get_active_event_id()
    with get_db() as conn:
        return conn.execute(
            "SELECT user_id, username, first_name, points FROM users WHERE event_id=? ORDER BY points DESC LIMIT ?",
            (event_id, limit)
        ).fetchall()


def get_all_channels(event_id: int = None):
    if event_id is None:
        event_id = get_active_event_id()
    with get_db() as conn:
        return conn.execute(
            "SELECT channel_id, channel_name FROM channels WHERE event_id=?",
            (event_id,)
        ).fetchall()


# ── 유저 명령어 ──────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    if update.effective_chat.type != "private":
        return

    event_id = get_active_event_id()
    event = get_active_event()

    # 이벤트 공지 — events.welcome_msg 또는 기본 메시지
    if event and event["welcome_msg"]:
        welcome = event["welcome_msg"]
    else:
        welcome = (
            "📣 현재 진행중인 이벤트는 🧩 Eigen Cloud 한국 커뮤니티 릴레이 입장이벤트입니다!\n\n"
            "✅ 아래 채널에 모두 입장해 주세요!\n\n"
            "👉 EigenCloud 한국 공지채널: https://t.me/EigenCloudKorea\n"
            "👉 EigenCloud 한국 커뮤니티: https://t.me/EigenCloud_KR_Community\n"
            "👉 불개미 채널: https://t.me/fireantcrypto\n"
            "👉 불개미 대화방: https://t.me/fireantgroup\n\n"
            "4개 채널 입장 후 아래 절차를 따라주세요!"
        )
    await update.message.reply_text(welcome, disable_web_page_preview=True)

    is_new = register_user(user.id, user.username or "", user.first_name or "")

    if is_new:
        await update.message.reply_text(
            "🔥 친구초대 이벤트 진행 중!\n\n"
            "친구를 초대하면 나와 친구 모두 10포인트씩 지급됩니다.\n"
            "포인트는 이벤트 종료 후 리워드로 환산됩니다.\n\n"
            "👇 아래에 초대한 분의 아이디를 입력해주세요!"
        )
        await update.message.reply_text(
            f"✅ 환영합니다, {user.first_name}님!\n"
            f"🎉 기본 +10 포인트가 지급됐습니다!\n\n"
            f"나를 이곳에 초대한 사람의 텔레그램 @유저네임을 입력하면\n"
            f"👉 나에게 +10포인트 추가 지급\n"
            f"👉 초대한 친구에게도 +10포인트 지급\n\n"
            f"(예: @fireantico)\n"
            f"없으면 /skip 입력"
        )
        return WAITING_REFERRER
    else:
        with get_db() as conn:
            info = conn.execute(
                "SELECT user_id FROM user_info WHERE user_id=? AND event_id=? AND agreed=1",
                (user.id, event_id)
            ).fetchone()

        if info:
            await update.message.reply_text(
                f"이미 등록된 유저입니다, {user.first_name}님!\n"
                f"/points 로 포인트를 확인하세요."
            )
        else:
            await update.message.reply_text(
                f"이미 등록된 유저입니다, {user.first_name}님!\n\n"
                f"📋 아직 당첨자 정보를 제출하지 않으셨습니다.\n"
                f"/inform 을 입력해 정보를 제출해주세요."
            )
        return ConversationHandler.END


async def receive_referrer_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if not text or text.startswith("/"):
        await update.message.reply_text(
            "@유저네임을 입력해주세요. (예: @fireantico)\n없으면 /skip"
        )
        return WAITING_REFERRER

    result = set_referrer(user.id, text)
    if len(result) == 4:
        ok, msg, referrer_uid, new_points = result
    else:
        ok, msg, referrer_uid = result
        new_points = 0

    if ok:
        invitee_name = user.first_name or user.username or "누군가"
        invitee_username = f"@{user.username}" if user.username else invitee_name
        await update.message.reply_text(
            f"✅ {msg}님을 초대자로 등록했습니다!\n💰 나에게 +10포인트, 초대자에게도 +10포인트 지급됐습니다."
        )
        try:
            await context.bot.send_message(
                chat_id=referrer_uid,
                text=(
                    f"🎉 {invitee_username}님이 회원님의 초대로 등록했습니다!\n\n"
                    f"📌 피초대자: {invitee_username}\n"
                    f"💰 지급 포인트: +10점\n"
                    f"🏆 현재 누적 포인트: {new_points}점"
                )
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(f"❌ {msg}")

    await update.message.reply_text(
        "📋 *당첨자 정보 입력을 시작합니다!*\n\n"
        "리워드 지급을 위해 아래 정보를 순서대로 입력해주세요.\n\n"
        "1️⃣ 이메일 주소를 입력해주세요.\n"
        "예) example@gmail.com",
        parse_mode="Markdown"
    )
    return INF_EMAIL


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    await update.message.reply_text("초대자 없이 등록했습니다.")

    await update.message.reply_text(
        "📋 *당첨자 정보 입력을 시작합니다!*\n\n"
        "리워드 지급을 위해 아래 정보를 순서대로 입력해주세요.\n\n"
        "1️⃣ 이메일 주소를 입력해주세요.\n"
        "예) example@gmail.com",
        parse_mode="Markdown"
    )
    return INF_EMAIL


async def cmd_setreferrer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text(
            "사용법: /setreferrer @유저네임\n예: /setreferrer @fireantico"
        )
        return

    referrer_input = args[0]
    result = set_referrer(user.id, referrer_input)
    if len(result) == 4:
        ok, msg, referrer_uid, new_points = result
    else:
        ok, msg, referrer_uid = result
        new_points = 0

    if ok:
        invitee_name = user.first_name or user.username or "누군가"
        invitee_username = f"@{user.username}" if user.username else invitee_name
        await update.message.reply_text(
            f"✅ {msg}님을 초대자로 등록했습니다!\n💰 나에게 +10포인트, 초대자에게도 +10포인트 지급됐습니다."
        )
        try:
            await context.bot.send_message(
                chat_id=referrer_uid,
                text=(
                    f"🎉 {invitee_username}님이 회원님의 초대로 등록했습니다!\n\n"
                    f"📌 피초대자: {invitee_username}\n"
                    f"💰 지급 포인트: +10점\n"
                    f"🏆 현재 누적 포인트: {new_points}점"
                )
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(f"❌ {msg}")


# ── /inform 플로우 ────────────────────────────────────────────────────────────

async def cmd_inform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """상품 수령 정보 입력 시작"""
    if update.effective_chat.type != "private":
        await update.message.reply_text("개인 채팅에서만 사용 가능합니다.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    event_id = get_active_event_id()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT email, telegram_id, phone, real_name, wallet FROM user_info WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
    if existing:
        real_name = existing['real_name'] or "-"
        wallet = existing['wallet'] or '미입력'
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ 정보 수정하기", callback_data="inf_edit_request")
        ]])
        await update.message.reply_text(
            "🎉 *정보 제출 완료!*\n\n"
            f"📧 이메일: {existing['email']}\n"
            f"💬 텔레그램: {existing['telegram_id']}\n"
            f"📱 휴대전화: {existing['phone']}\n"
            f"👤 빗썸 실명: {real_name}\n"
            f"💎 EVM 지갑: {wallet}\n\n"
            "리워드는 순위 확정 후 순차적으로 지급됩니다.\n감사합니다! 🔥\n\n"
            "당신은 모든 정보를 잘 제출했습니다!\n\n"
            "💡 정보를 수정하고 싶다면 아래 버튼을 누르세요.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📋 *상품 수령 정보 입력*\n\n"
        "리워드 지급을 위해 아래 정보를 순서대로 입력해주세요.\n\n"
        "1️⃣ 이메일 주소를 입력해주세요.\n"
        "예) example@gmail.com",
        parse_mode="Markdown"
    )
    return INF_EMAIL


async def inf_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text("❌ 올바른 이메일 형식이 아닙니다. 다시 입력해주세요.\n예) example@gmail.com")
        return INF_EMAIL

    context.user_data["inf_email"] = email
    await update.message.reply_text(
        f"✅ 이메일: {email}\n\n"
        "2️⃣ 텔레그램 아이디를 입력해주세요. (@포함)\n"
        "예) @fireantico"
    )
    return INF_TG


async def inf_receive_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg = update.message.text.strip()
    if not tg.startswith("@"):
        tg = "@" + tg
    context.user_data["inf_tg"] = tg
    await update.message.reply_text(
        f"✅ 텔레그램: {tg}\n\n"
        "3️⃣ 휴대전화 번호를 입력해주세요.\n"
        "예) 010-1234-5678"
    )
    return INF_PHONE


async def inf_receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data["inf_phone"] = phone
    await update.message.reply_text(
        f"✅ 휴대전화: {phone}\n\n"
        "4️⃣ 빗썸에 가입한 실명을 입력해주세요.\n"
        "예) 홍길동"
    )
    return INF_REALNAME


async def inf_receive_realname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    real_name = update.message.text.strip()
    context.user_data["inf_real_name"] = real_name

    await update.message.reply_text(
        f"✅ 빗썸 실명: {real_name}\n\n"
        "4️⃣ EVM 지갑주소를 입력해주세요.\n\n"
        "⚠️ 거래소 지갑은 불가합니다. 반드시 개인 지갑 주소를 입력해주세요!\n"
        "예) 0x1234...abcd"
    )
    return INF_WALLET


async def inf_receive_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    context.user_data["inf_wallet"] = wallet

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 동의합니다", callback_data="inf_agree_yes"),
        InlineKeyboardButton("❌ 동의하지 않습니다", callback_data="inf_agree_no"),
    ]])
    await update.message.reply_text(
        f"✅ EVM 지갑주소: {wallet}\n\n"
        "5️⃣ *개인정보 수집·이용 동의*\n\n"
        "수집 항목: 이메일, 텔레그램 아이디, 휴대전화 번호, 빗썸 실명, EVM 지갑주소\n"
        "수집 목적: 이벤트 리워드 지급\n"
        "보유 기간: 리워드 지급 완료 후 6개월\n\n"
        "위 내용에 동의하십니까?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return INF_AGREE


async def inf_agree_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    event_id = get_active_event_id()

    if query.data == "inf_agree_no":
        await query.edit_message_text("❌ 개인정보 수집에 동의하지 않아 정보 입력이 취소되었습니다.")
        return ConversationHandler.END

    email     = context.user_data.get("inf_email", "")
    tg        = context.user_data.get("inf_tg", "")
    phone     = context.user_data.get("inf_phone", "")
    real_name = context.user_data.get("inf_real_name", "")
    wallet    = context.user_data.get("inf_wallet", "")

    inserted = False
    with get_db() as conn:
        existing = conn.execute(
            "SELECT user_id FROM user_info WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO user_info (user_id, event_id, email, telegram_id, phone, real_name, wallet, agreed) VALUES (?,?,?,?,?,?,?,1)",
                (user_id, event_id, email, tg, phone, real_name, wallet)
            )
            inserted = True
        user_row = conn.execute(
            "SELECT points FROM users WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
        points = user_row["points"] if user_row else 0
        rank_row = conn.execute(
            "SELECT COUNT(*)+1 as rank FROM users WHERE points > ? AND event_id=?",
            (points, event_id)
        ).fetchone()
        rank = rank_row["rank"] if rank_row else "-"

    if inserted:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            append_to_sheet([now_str, str(user_id), tg, query.from_user.first_name or "", email, phone, real_name, wallet, points, rank], event_id)
        except Exception as e:
            logging.getLogger(__name__).error(f"Sheets 기록 예외: {e}")

    completion_text = (
        "🎉 *정보 제출 완료!*\n\n"
        f"📧 이메일: {email}\n"
        f"💬 텔레그램: {tg}\n"
        f"📱 휴대전화: {phone}\n"
        f"👤 빗썸 실명: {real_name}\n"
        f"💎 EVM 지갑: {wallet}\n\n"
        "리워드는 순위 확정 후 순차적으로 지급됩니다.\n감사합니다! 🔥\n\n"
        "당신은 모든 정보를 잘 제출했습니다!\n\n"
        "💡 정보를 수정하고 싶다면 아래 버튼을 누르세요."
    )
    edit_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✏️ 정보 수정하기", callback_data="inf_edit_request")
    ]])
    try:
        await query.edit_message_text(completion_text, parse_mode="Markdown", reply_markup=edit_keyboard)
    except Exception:
        await query.get_bot().send_message(
            chat_id=user_id,
            text=completion_text,
            parse_mode="Markdown",
            reply_markup=edit_keyboard
        )
    return ConversationHandler.END


async def inf_edit_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 삭제 후 재제출", callback_data="inf_edit_confirm"),
        InlineKeyboardButton("❌ 취소", callback_data="inf_edit_cancel"),
    ]])
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        "⚠️ 기존 제출 정보를 삭제하고 다시 입력하시겠습니까?\n\n"
        "삭제 후에는 되돌릴 수 없습니다.",
        reply_markup=keyboard
    )


async def inf_edit_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    event_id = get_active_event_id()

    with get_db() as conn:
        conn.execute("DELETE FROM user_info WHERE user_id=? AND event_id=?", (user_id, event_id))

    threading.Thread(target=delete_from_sheet, args=(user_id, event_id), daemon=True).start()

    await query.edit_message_text("🗑️ 기존 정보가 삭제되었습니다. 다시 입력을 시작합니다.")

    context.user_data.clear()
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "📋 *상품 수령 정보 입력*\n\n"
            "리워드 지급을 위해 아래 정보를 순서대로 입력해주세요.\n\n"
            "1️⃣ 이메일 주소를 입력해주세요.\n"
            "예) example@gmail.com"
        ),
        parse_mode="Markdown"
    )
    return INF_EMAIL


async def inf_edit_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ 수정이 취소되었습니다.")


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    user_id = update.effective_user.id
    event_id = get_active_event_id()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT wallet FROM user_info WHERE user_id=? AND event_id=? AND agreed=1",
            (user_id, event_id)
        ).fetchone()

    if not existing:
        await update.message.reply_text("먼저 /inform 으로 정보를 제출해주세요.")
        return ConversationHandler.END

    current = existing['wallet'] or '미입력'
    await update.message.reply_text(
        f"💎 *EVM 지갑주소 입력*\n\n"
        f"현재 등록된 주소: `{current}`\n\n"
        "⚠️ 거래소 지갑은 불가합니다. 반드시 개인 지갑 주소를 입력해주세요!\n"
        "(MetaMask, Rabby 등 개인 지갑 주소)\n\n"
        "새 지갑주소를 입력해주세요:\n예) 0x1234...abcd",
        parse_mode="Markdown"
    )
    return WALLET_INPUT


async def wallet_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    user_id = update.effective_user.id
    event_id = get_active_event_id()
    sheet_id = get_sheets_id(event_id)

    with get_db() as conn:
        conn.execute("UPDATE user_info SET wallet=? WHERE user_id=? AND event_id=?", (wallet, user_id, event_id))

    try:
        def update_sheet():
            try:
                service = build_sheets_service()
                sheet_name = GSHEETS_RANGE.split('!')[0]
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=f'{sheet_name}!B:B'
                ).execute()
                values = result.get('values', [])
                for i, row in enumerate(values):
                    if row and row[0] == str(user_id):
                        service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=f'{sheet_name}!H{i+1}',
                            valueInputOption='RAW',
                            body={'values': [[wallet]]}
                        ).execute()
                        break
            except Exception as e:
                logging.getLogger(__name__).error(f"Sheets wallet 업데이트 오류: {e}")
        threading.Thread(target=update_sheet, daemon=True).start()
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ EVM 지갑주소가 등록되었습니다!\n\n"
        f"💎 `{wallet}`\n\n"
        "⚠️ 거래소 지갑을 입력하셨다면 /wallet 으로 다시 수정해주세요.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cmd_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    user_id = update.effective_user.id
    event_id = get_active_event_id()

    # user_info에 행이 없으면 자동 생성 (inform 없이도 reward 가능)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT bithumb_wallet FROM user_info WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT OR IGNORE INTO user_info (user_id, event_id, agreed) VALUES (?, ?, 1)",
                (user_id, event_id)
            )

    current = (existing['bithumb_wallet'] if existing else None) or '미입력'
    await update.message.reply_text(
        f"🪙 *빗썸 Eigen 지갑주소를 입력하세요.*\n\n"
        f"현재 등록된 주소: `{current}`\n\n"
        "빗썸 거래소의 **Eigen 코인 입금 주소**를 붙여넣기 해주세요.",
        parse_mode="Markdown"
    )
    return REWARD_INPUT


async def reward_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bithumb_wallet = update.message.text.strip()
    user_id = update.effective_user.id
    event_id = get_active_event_id()
    sheet_id = get_sheets_id(event_id)

    with get_db() as conn:
        conn.execute(
            "UPDATE user_info SET bithumb_wallet=? WHERE user_id=? AND event_id=?",
            (bithumb_wallet, user_id, event_id)
        )

    try:
        def update_reward_sheet():
            try:
                service = build_sheets_service()
                sheet_name = GSHEETS_RANGE.split('!')[0]
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=f'{sheet_name}!B:B'
                ).execute()
                values = result.get('values', [])
                for i, row in enumerate(values):
                    if row and row[0] == str(user_id):
                        service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=f'{sheet_name}!K{i+1}',
                            valueInputOption='RAW',
                            body={'values': [[bithumb_wallet]]}
                        ).execute()
                        break
            except Exception as e:
                logging.getLogger(__name__).error(f"Sheets bithumb_wallet 업데이트 오류: {e}")
        threading.Thread(target=update_reward_sheet, daemon=True).start()
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ 제출 완료!\n\n"
        f"📋 등록된 주소: `{bithumb_wallet}`\n\n"
        "수정이 필요하면 /reward 를 다시 입력하세요.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cmd_export_inform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    event_id = get_active_event_id()

    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.username, u.first_name, i.telegram_id, i.email, i.phone, i.real_name, i.wallet, i.submitted_at,
                   u.points,
                   (SELECT COUNT(*) FROM users u2 WHERE u2.referrer_id = u.user_id AND u2.event_id = ?) as invite_count
            FROM user_info i
            JOIN users u ON u.user_id = i.user_id AND u.event_id = i.event_id
            WHERE i.agreed = 1 AND i.event_id = ?
            ORDER BY u.points DESC
        """, (event_id, event_id)).fetchall()

    if not rows:
        await update.message.reply_text("제출된 정보가 없습니다.")
        return

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["순위", "텔레그램아이디", "이름", "포인트", "초대수", "이메일", "전화번호", "빗썸실명", "지갑주소", "제출일시"])
    for i, r in enumerate(rows, 1):
        writer.writerow([i, r["telegram_id"] or r["username"], r["first_name"],
                         r["points"], r["invite_count"], r["email"], r["phone"],
                         r["real_name"] or "", r["wallet"] or "", r["submitted_at"]])

    await update.message.reply_document(
        document=buf.getvalue().encode("utf-8-sig"),
        filename="eigencloud_inform.csv",
        caption=f"📋 정보 제출 현황 — 총 {len(rows)}명 (이벤트 ID: {event_id})"
    )


async def cmd_inform_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    event_id = get_active_event_id()
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM users WHERE ever_registered=1 AND event_id=?", (event_id,)).fetchone()["c"]
        submitted = conn.execute("SELECT COUNT(*) as c FROM user_info WHERE agreed=1 AND event_id=?", (event_id,)).fetchone()["c"]
    await update.message.reply_text(f"📊 정보 제출 현황 (이벤트 ID: {event_id})\n전체 등록자: {total}명\n제출 완료: {submitted}명\n미제출: {total - submitted}명")


async def cmd_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    row = get_user(user.id)
    if not row:
        await update.message.reply_text("아직 등록되지 않았습니다. /start 로 시작해주세요.")
        return
    await update.message.reply_text(
        f"🏆 {user.first_name}님의 포인트\n"
        f"현재 포인트: {row['points']}점"
    )


async def cmd_myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    event_id = get_active_event_id()
    with get_db() as conn:
        info = conn.execute(
            "SELECT email, telegram_id, phone, real_name, wallet, bithumb_wallet, submitted_at FROM user_info WHERE user_id=? AND event_id=? AND agreed=1",
            (user_id, event_id)
        ).fetchone()

    if not info:
        await update.message.reply_text("⚠️ 아직 제출된 정보가 없습니다. /inform 으로 먼저 정보를 제출해주세요.")
        return

    await update.message.reply_text(
        "📋 *내 정보 조회*\n\n"
        f"📧 이메일: {info['email']}\n"
        f"💬 텔레그램: {info['telegram_id']}\n"
        f"📱 휴대전화: {info['phone']}\n"
        f"👤 빗썸 실명: {info['real_name'] or '-'}\n"
        f"💎 EVM 지갑: {info['wallet'] or '미입력'}\n"
        f"🪙 빗썸 Eigen 입금주소: {info['bithumb_wallet'] or '미입력'}\n"
        f"🕒 제출일시: {info['submitted_at']}",
        parse_mode="Markdown"
    )


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    board = get_leaderboard(10)
    if not board:
        await update.message.reply_text("아직 등록된 유저가 없습니다.")
        return

    lines = ["🏆 TOP 10 순위\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(board):
        prefix = medals[i] if i < 3 else f"{i+1}."
        name = row["first_name"] or row["username"] or str(row["user_id"])
        lines.append(f"{prefix} {name} — {row['points']}점")

    await update.message.reply_text("\n".join(lines))


# ── 관리자 명령어 ────────────────────────────────────────────────────────────
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ 관리자 전용 명령어입니다.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


@admin_only
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event = get_active_event()
    event_name = event["name"] if event else "없음"
    keyboard = [
        [InlineKeyboardButton("📊 리더보드", callback_data="admin_leaderboard"),
         InlineKeyboardButton("📤 CSV 내보내기", callback_data="admin_export")],
        [InlineKeyboardButton("📋 채널 목록", callback_data="admin_channels"),
         InlineKeyboardButton("📅 이벤트 기간", callback_data="admin_period")],
        [InlineKeyboardButton("🔴 포인트 초기화", callback_data="admin_reset")],
    ]
    await update.message.reply_text(
        f"🛠 관리자 메뉴\n📍 활성 이벤트: {event_name} (ID: {get_active_event_id()})",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@admin_only
async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = get_leaderboard(20)
    if not board:
        await update.message.reply_text("등록된 유저가 없습니다.")
        return
    event_id = get_active_event_id()
    lines = [f"📊 전체 포인트 순위 (이벤트 ID: {event_id})\n"]
    for i, row in enumerate(board):
        name = row["first_name"] or row["username"] or str(row["user_id"])
        lines.append(f"{i+1}. {name} ({row['user_id']}) — {row['points']}점")
    await update.message.reply_text("\n".join(lines))


@admin_only
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_id = get_active_event_id()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT u.user_id, u.username, u.first_name, u.points, u.referrer_id, u.registered_at,
                   i.bithumb_wallet
            FROM users u
            LEFT JOIN user_info i ON i.user_id = u.user_id AND i.event_id = u.event_id
            WHERE u.event_id = ?
            ORDER BY u.points DESC
            """, (event_id,)
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["user_id", "username", "first_name", "points", "referrer_id", "registered_at", "빗썸Eigen주소"])
    for row in rows:
        writer.writerow([row["user_id"], row["username"], row["first_name"],
                         row["points"], row["referrer_id"], row["registered_at"], row["bithumb_wallet"] or ""])

    buf.seek(0)
    filename = f"referral_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}_event{event_id}.csv"
    await update.message.reply_document(
        document=buf.getvalue().encode("utf-8-sig"),
        filename=filename,
        caption=f"총 {len(rows)}명 데이터 (이벤트 ID: {event_id})"
    )


@admin_only
async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /addchannel <channel_id>")
        return
    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("채널 ID는 숫자여야 합니다.")
        return

    event_id = get_active_event_id()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO channels (channel_id, event_id) VALUES (?,?)",
            (channel_id, event_id)
        )
    await update.message.reply_text(f"✅ 채널 {channel_id} 추가됐습니다. (이벤트 ID: {event_id})")


@admin_only
async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /removechannel <channel_id>")
        return
    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("채널 ID는 숫자여야 합니다.")
        return

    event_id = get_active_event_id()
    with get_db() as conn:
        conn.execute("DELETE FROM channels WHERE channel_id=? AND event_id=?", (channel_id, event_id))
    await update.message.reply_text(f"✅ 채널 {channel_id} 제거됐습니다. (이벤트 ID: {event_id})")


@admin_only
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_id = get_active_event_id()
    keyboard = [
        [InlineKeyboardButton("⚠️ 정말 초기화", callback_data="confirm_reset"),
         InlineKeyboardButton("❌ 취소", callback_data="cancel_reset")]
    ]
    await update.message.reply_text(
        f"⚠️ 이벤트 ID {event_id}의 모든 유저 포인트를 초기화합니다. 계속하시겠습니까?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@admin_only
async def cmd_setperiod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /setperiod <시작일 YYYY-MM-DD> <종료일 YYYY-MM-DD>")
        return
    start, end = context.args[0], context.args[1]
    event_id = get_active_event_id()
    with get_db() as conn:
        conn.execute(
            "UPDATE events SET start_date=?, end_date=? WHERE id=?",
            (start, end, event_id)
        )
    await update.message.reply_text(f"✅ 이벤트 기간: {start} ~ {end} (이벤트 ID: {event_id})")


# ── 이벤트 관리 명령어 ──────────────────────────────────────────────────────
@admin_only
async def cmd_newevent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/newevent "이벤트명" 시작일 종료일"""
    if len(context.args) < 3:
        await update.message.reply_text('사용법: /newevent "이벤트명" 시작일 종료일\n예: /newevent "새 이벤트" 2026-05-01 2026-05-31')
        return

    name = context.args[0]
    start = context.args[1]
    end = context.args[2]

    with get_db() as conn:
        # 기존 활성 이벤트 비활성화
        conn.execute("UPDATE events SET is_active=0 WHERE is_active=1")
        # 새 이벤트 생성
        cursor = conn.execute(
            "INSERT INTO events (name, start_date, end_date, is_active) VALUES (?,?,?,1)",
            (name, start, end)
        )
        new_id = cursor.lastrowid

    await update.message.reply_text(
        f"✅ 새 이벤트 생성 완료!\n"
        f"📌 ID: {new_id}\n"
        f"📋 이름: {name}\n"
        f"📅 기간: {start} ~ {end}\n\n"
        f"/seteventmsg 로 환영 메시지를 설정하세요."
    )


@admin_only
async def cmd_endevent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """현재 활성 이벤트 종료"""
    event_id = get_active_event_id()
    with get_db() as conn:
        conn.execute("UPDATE events SET is_active=0 WHERE id=?", (event_id,))
    await update.message.reply_text(f"✅ 이벤트 ID {event_id} 가 종료되었습니다. (is_active=0)")


@admin_only
async def cmd_switchevent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/switchevent 이벤트ID"""
    if not context.args:
        await update.message.reply_text("사용법: /switchevent <이벤트ID>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("이벤트 ID는 숫자여야 합니다.")
        return

    with get_db() as conn:
        event = conn.execute("SELECT id, name FROM events WHERE id=?", (target_id,)).fetchone()
        if not event:
            await update.message.reply_text(f"❌ 이벤트 ID {target_id} 를 찾을 수 없습니다.")
            return
        conn.execute("UPDATE events SET is_active=0 WHERE is_active=1")
        conn.execute("UPDATE events SET is_active=1 WHERE id=?", (target_id,))

    await update.message.reply_text(f"✅ 활성 이벤트가 전환되었습니다.\n📌 ID: {target_id}\n📋 이름: {event['name']}")


@admin_only
async def cmd_eventlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """전체 이벤트 목록"""
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, start_date, end_date, is_active, created_at FROM events ORDER BY id").fetchall()

    if not rows:
        await update.message.reply_text("등록된 이벤트가 없습니다.")
        return

    lines = ["📋 전체 이벤트 목록\n"]
    for r in rows:
        status = "🟢 활성" if r["is_active"] else "⚪ 비활성"
        lines.append(
            f"{status} ID:{r['id']} — {r['name']}\n"
            f"   📅 {r['start_date'] or '?'} ~ {r['end_date'] or '?'} (생성: {r['created_at']})"
        )
    await update.message.reply_text("\n".join(lines))


@admin_only
async def cmd_seteventmsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/seteventmsg 메시지내용 — 현재 활성 이벤트의 welcome_msg 수정"""
    if not context.args:
        await update.message.reply_text("사용법: /seteventmsg <환영 메시지>\n현재 메시지를 보려면 인자 없이 입력하세요.")
        # Show current msg
        event = get_active_event()
        if event and event["welcome_msg"]:
            await update.message.reply_text(f"현재 welcome_msg:\n\n{event['welcome_msg']}")
        else:
            await update.message.reply_text("현재 welcome_msg: (기본 메시지 사용 중)")
        return

    msg = " ".join(context.args)
    event_id = get_active_event_id()
    with get_db() as conn:
        conn.execute("UPDATE events SET welcome_msg=? WHERE id=?", (msg, event_id))
    await update.message.reply_text(f"✅ 이벤트 ID {event_id}의 환영 메시지가 업데이트되었습니다.")


# ── 콜백 쿼리 ────────────────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if update.effective_user.id != ADMIN_ID and data.startswith("admin_"):
        await query.edit_message_text("⛔ 관리자 전용입니다.")
        return

    if data == "admin_leaderboard":
        board = get_leaderboard(20)
        lines = [f"📊 전체 포인트 순위 (이벤트 ID: {get_active_event_id()})\n"]
        for i, row in enumerate(board):
            name = row["first_name"] or row["username"] or str(row["user_id"])
            lines.append(f"{i+1}. {name} ({row['user_id']}) — {row['points']}점")
        await query.edit_message_text("\n".join(lines) if board else "데이터 없음")

    elif data == "admin_export":
        await query.edit_message_text("CSV 내보내기는 /export 명령어를 사용하세요.")

    elif data == "admin_channels":
        channels = get_all_channels()
        if not channels:
            await query.edit_message_text("등록된 채널이 없습니다.")
        else:
            lines = ["📋 등록된 채널\n"]
            for ch in channels:
                lines.append(f"• {ch['channel_id']} ({ch['channel_name'] or '이름 없음'})")
            await query.edit_message_text("\n".join(lines))

    elif data == "admin_period":
        event = get_active_event()
        if event and event["start_date"]:
            await query.edit_message_text(f"📅 이벤트 기간: {event['start_date']} ~ {event['end_date']}")
        else:
            await query.edit_message_text("📅 이벤트 기간: 상시 운영 중\n변경: /setperiod YYYY-MM-DD YYYY-MM-DD")

    elif data == "admin_reset":
        event_id = get_active_event_id()
        keyboard = [
            [InlineKeyboardButton("⚠️ 정말 초기화", callback_data="confirm_reset"),
             InlineKeyboardButton("❌ 취소", callback_data="cancel_reset")]
        ]
        await query.edit_message_text(
            f"⚠️ 이벤트 ID {event_id}의 모든 유저 포인트를 0으로 초기화합니다. 계속하시겠습니까?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "confirm_reset":
        event_id = get_active_event_id()
        with get_db() as conn:
            conn.execute("UPDATE users SET points=0, referrer_id=NULL WHERE event_id=?", (event_id,))
        await query.edit_message_text(f"✅ 포인트 초기화 완료. (이벤트 ID: {event_id})")

    elif data == "cancel_reset":
        await query.edit_message_text("❌ 초기화 취소됐습니다.")


# ── 채널 멤버 이벤트 (신규 입장 / 퇴장) ────────────────────────────────────
async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    channel_id = result.chat.id
    event_id = get_active_event_id()
    with get_db() as conn:
        registered = conn.execute(
            "SELECT channel_id FROM channels WHERE channel_id=? AND event_id=?",
            (channel_id, event_id)
        ).fetchone()
    if not registered:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    target_user = result.new_chat_member.user

    if target_user.is_bot:
        return

    if old_status in ("left", "kicked", "restricted") and new_status == "member":
        try:
            mention = f'<a href="tg://user?id={target_user.id}">{target_user.first_name}</a>'
            bot_username = (await context.bot.get_me()).username
            sent = await context.bot.send_message(
                chat_id=result.chat.id,
                text=(
                    f"🎉 {mention}님 환영합니다!\n\n"
                    f"🔥 친구초대 이벤트 진행 중!\n"
                    f"포인트를 받으려면 아래 봇에서 /start 를 눌러주세요 👇\n"
                    f"@{bot_username}"
                ),
                parse_mode="HTML"
            )
            async def delete_later(chat_id, msg_id):
                import asyncio
                await asyncio.sleep(5)
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            import asyncio
            asyncio.create_task(delete_later(result.chat.id, sent.message_id))
        except Exception as e:
            logger.warning("채널 환영 메시지 실패 (user_id=%s): %s", target_user.id, e)

    elif old_status in ("member", "administrator", "creator", "restricted") and new_status in ("left", "kicked"):
        user_id = target_user.id
        logger.info("채널 퇴장 감지 user_id=%s channel_id=%s", user_id, channel_id)

        with get_db() as conn:
            user_row = conn.execute(
                "SELECT id, points, referrer_id FROM users WHERE user_id=? AND event_id=?",
                (user_id, event_id)
            ).fetchone()

            if user_row:
                referrer_id = user_row["referrer_id"]
                conn.execute("UPDATE users SET points=0 WHERE id=?", (user_row["id"],))
                if referrer_id:
                    conn.execute(
                        "UPDATE users SET points = MAX(0, points - 10) WHERE user_id=? AND event_id=?",
                        (referrer_id, event_id)
                    )
                    logger.info("초대자 포인트 회수 referrer_id=%s", referrer_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="채널을 퇴장하여 포인트가 몰수되었습니다."
            )
        except Exception as e:
            logger.warning("퇴장 DM 발송 실패 (user_id=%s): %s", user_id, e)


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    init_db()
    token = get_token()

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            WAITING_REFERRER: [
                CommandHandler("skip", cmd_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_referrer_id),
            ],
            INF_EMAIL:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_email)],
            INF_TG:       [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_tg)],
            INF_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_phone)],
            INF_REALNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_realname)],
            INF_WALLET:   [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_wallet)],
            INF_AGREE:    [CallbackQueryHandler(inf_agree_callback, pattern="^inf_agree_")],
        },
        fallbacks=[CommandHandler("skip", cmd_skip)],
    )
    app.add_handler(conv)

    inform_conv = ConversationHandler(
        entry_points=[
            CommandHandler("inform", cmd_inform),
            CallbackQueryHandler(inf_edit_confirm_callback, pattern="^inf_edit_confirm$"),
        ],
        states={
            INF_EMAIL:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_email)],
            INF_TG:       [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_tg)],
            INF_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_phone)],
            INF_REALNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_realname)],
            INF_WALLET:   [MessageHandler(filters.TEXT & ~filters.COMMAND, inf_receive_wallet)],
            INF_AGREE:    [CallbackQueryHandler(inf_agree_callback, pattern="^inf_agree_")],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        per_message=False,
    )
    app.add_handler(inform_conv)

    wallet_conv = ConversationHandler(
        entry_points=[CommandHandler("wallet", cmd_wallet)],
        states={
            WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_receive)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(wallet_conv)

    reward_conv = ConversationHandler(
        entry_points=[CommandHandler("reward", cmd_reward)],
        states={
            REWARD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reward_receive)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(reward_conv)

    # 유저 명령어
    app.add_handler(CommandHandler("points", cmd_points))
    app.add_handler(CommandHandler("setreferrer", cmd_setreferrer))
    app.add_handler(CommandHandler("myinfo", cmd_myinfo))
    app.add_handler(CommandHandler("rank", cmd_rank))

    # 관리자 명령어
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))
    app.add_handler(CommandHandler("removechannel", cmd_removechannel))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("setperiod", cmd_setperiod))
    app.add_handler(CommandHandler("export_inform", cmd_export_inform))
    app.add_handler(CommandHandler("inform_count", cmd_inform_count))

    # 이벤트 관리 명령어
    app.add_handler(CommandHandler("newevent", cmd_newevent))
    app.add_handler(CommandHandler("endevent", cmd_endevent))
    app.add_handler(CommandHandler("switchevent", cmd_switchevent))
    app.add_handler(CommandHandler("eventlist", cmd_eventlist))
    app.add_handler(CommandHandler("seteventmsg", cmd_seteventmsg))

    # 정보 수정 관련 콜백
    app.add_handler(CallbackQueryHandler(inf_edit_request_callback, pattern="^inf_edit_request$"))
    app.add_handler(CallbackQueryHandler(inf_edit_cancel_callback, pattern="^inf_edit_cancel$"))

    # 콜백
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 채널 멤버 변경 이벤트
    app.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))

    logger.info("🤖 Referral Bot 시작! (이벤트 격리 지원)")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
