#!/usr/bin/env python3
import asyncio
import os
import pytz
import json
import logging
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, date, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "task34.db"
GOOGLE_TOKEN_PATH = Path("/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json")
KST = pytz.timezone("Asia/Seoul")

TODO_THREAD_ID = 151
MAIN_CHAT_ID = -1002585427625
GENERAL_THREAD_ID = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("task34bot")

SUPABASE_URL = "https://npdzxtnzjkdzwbpphduf.supabase.co"
SUPABASE_KEY = "sb_publishable_-TVlChpvyWRZEweQ8wHe2g_WxQD5nql"

PROJECT_KEYWORD_MAP = [
    ("eigen", "#EigenCloud"),
    ("d3", "#D3Exchange"),
    ("infinit", "#INFINIT"),
    ("monday", "#MondayTrade"),
    ("ethgas", "#Ethgas"),
    ("blockstreet", "#BlockStreet"),
    ("virtuals", "#Virtuals"),
    ("ethena", "#Ethena"),
    ("everything", "#Everything"),
    ("kgen", "#KGEN"),
    ("pharos", "#Pharos"),
    ("aligned", "#Aligned"),
    ("stable", "#Stable"),
]


def detect_project(task_text: str) -> str:
    lower = (task_text or "").lower()
    for keyword, project in PROJECT_KEYWORD_MAP:
        if keyword in lower:
            return project
    return "#기타"


@dataclass
class TaskItem:
    event_id: str
    summary: str
    when_label: str
    due_date: datetime
    overdue: bool
    d_label: str


def get_bot_token() -> str:
    # 환경변수 우선 사용 (LaunchAgent 환경)
    import os
    env_token = os.environ.get("TASK34_BOT_TOKEN", "")
    if env_token:
        return env_token
    # Keychain fallback
    return subprocess.check_output(
        ["security", "find-generic-password", "-s", "task34-bot-token", "-w"],
        text=True,
    ).strip()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS email_map (
                email TEXT PRIMARY KEY,
                telegram_username TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS group_chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                activated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                task TEXT NOT NULL,
                due_date TEXT,
                done INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute("PRAGMA table_info(todos)")
        todo_columns = {row[1] for row in cur.fetchall()}
        if "completed_at" not in todo_columns:
            cur.execute("ALTER TABLE todos ADD COLUMN completed_at TEXT")
        if "project" not in todo_columns:
            cur.execute("ALTER TABLE todos ADD COLUMN project TEXT")
        if "priority" not in todo_columns:
            cur.execute("ALTER TABLE todos ADD COLUMN priority INTEGER DEFAULT 2")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS live_message (
                chat_id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def db_connect():
    return sqlite3.connect(DB_PATH)


def _supabase_headers() -> dict:
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }


def _dashboard_headers() -> dict:
    return {
        **_supabase_headers(),
        "Prefer": "return=representation",
    }


def _is_dashboard_thread(update: Update) -> bool:
    return (
        update.effective_chat is not None
        and update.effective_chat.id == MAIN_CHAT_ID
        and update.message is not None
        and update.message.message_thread_id == TODO_THREAD_ID
    )


def dashboard_find_client_by_keyword(keyword: str) -> Optional[dict]:
    q = keyword.strip()
    if not q:
        return None
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/clients",
            headers=_dashboard_headers(),
            params={
                "select": "id,client",
                "client": f"ilike.*{q}*",
                "order": "id.asc",
                "limit": "1",
            },
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase client lookup failed: %s %s", resp.status_code, resp.text)
            return None
        rows = resp.json()
        return rows[0] if rows else None
    except Exception as e:
        logger.warning("Supabase client lookup exception: %s", e)
        return None


def dashboard_update_project(client_id: int, next_action: str, notes: str) -> bool:
    try:
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/clients?id=eq.{client_id}",
            headers=_dashboard_headers(),
            data=json.dumps({"next_action": next_action, "notes": notes}, ensure_ascii=False),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase project update failed: %s %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:
        logger.warning("Supabase project update exception: %s", e)
        return False


def dashboard_upsert_deal(client_name: str, category: str) -> bool:
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/clients?on_conflict=client",
            headers={**_dashboard_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
            data=json.dumps({"client": client_name, "category": category}, ensure_ascii=False),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase deal upsert failed: %s %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:
        logger.warning("Supabase deal upsert exception: %s", e)
        return False


def dashboard_update_deal_category(client_id: int, category: str) -> bool:
    try:
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/clients?id=eq.{client_id}",
            headers=_dashboard_headers(),
            data=json.dumps({"category": category}, ensure_ascii=False),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase deal category update failed: %s %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:
        logger.warning("Supabase deal category update exception: %s", e)
        return False


def dashboard_list_by_category(category: str) -> List[str]:
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/clients",
            headers=_dashboard_headers(),
            params={
                "select": "client",
                "category": f"eq.{category}",
                "order": "client.asc",
            },
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase list by category failed: %s %s", resp.status_code, resp.text)
            return []
        rows = resp.json()
        return [r.get("client") for r in rows if r.get("client")]
    except Exception as e:
        logger.warning("Supabase list by category exception: %s", e)
        return []



def dashboard_list_projects_full(category: str) -> List[dict]:
    """카테고리별 프로젝트 전체 정보(client, next_action, notes) 반환."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/clients",
            headers=_dashboard_headers(),
            params={
                "select": "client,next_action,notes",
                "category": f"eq.{category}",
                "order": "client.asc",
            },
            timeout=15,
        )
        if not resp.ok:
            return []
        return resp.json()
    except Exception as e:
        logger.warning("dashboard_list_projects_full exception: %s", e)
        return []

def upsert_to_supabase(task_row: dict) -> None:
    """SQLite todos -> Supabase tasks 동기화 (add 시 INSERT)."""
    payload = {
        "task": task_row.get("task"),
        "assignee": task_row.get("assignee"),
        "status": "Done" if task_row.get("done") else "To-Do",
        "due_date": task_row.get("due_date"),
    }
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/tasks",
            headers={**_supabase_headers(), "Prefer": "return=representation"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase upsert(add) failed: %s %s", resp.status_code, resp.text)
    except Exception as e:
        logger.warning("Supabase upsert(add) exception: %s", e)


def mark_done_in_supabase(task_row: dict) -> None:
    """/done 시 Supabase tasks status='Done' 반영."""
    task_text = task_row.get("task")
    assignee = task_row.get("assignee")
    due_date = task_row.get("due_date")
    if not task_text:
        return

    try:
        query = (
            f"task=eq.{requests.utils.quote(task_text, safe='')}&"
            f"assignee=eq.{requests.utils.quote(assignee or '', safe='')}&"
            f"order=created_at.desc&limit=1"
        )
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/tasks?select=id,status&{query}",
            headers=_supabase_headers(),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase lookup(done) failed: %s %s", resp.status_code, resp.text)
            return
        rows = resp.json()
        if not rows:
            upsert_to_supabase(
                {"task": task_text, "assignee": assignee, "due_date": due_date, "done": 1}
            )
            return

        target_id = rows[0].get("id")
        if target_id is None:
            return
        patch = requests.patch(
            f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{target_id}",
            headers=_supabase_headers(),
            data=json.dumps({"status": "Done"}, ensure_ascii=False),
            timeout=15,
        )
        if not patch.ok:
            logger.warning("Supabase update(done) failed: %s %s", patch.status_code, patch.text)
    except Exception as e:
        logger.warning("Supabase update(done) exception: %s", e)


def delete_from_supabase(task_text: str, assignee: str) -> None:
    """/del 시 Supabase tasks에서 동일 task+assignee 삭제."""
    if not task_text:
        return
    try:
        q_task = requests.utils.quote(task_text, safe='')
        q_assignee = requests.utils.quote(assignee or '', safe='')
        resp = requests.delete(
            f"{SUPABASE_URL}/rest/v1/tasks?task=eq.{q_task}&assignee=eq.{q_assignee}",
            headers=_supabase_headers(),
            timeout=15,
        )
        if not resp.ok:
            logger.warning("Supabase delete(del) failed: %s %s", resp.status_code, resp.text)
    except Exception as e:
        logger.warning("Supabase delete(del) exception: %s", e)


def refresh_google_access_token(token_data: dict) -> dict:
    payload = {
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token",
    }
    resp = requests.post(token_data.get("token_uri", "https://oauth2.googleapis.com/token"), data=payload, timeout=20)
    resp.raise_for_status()
    refreshed = resp.json()
    token_data["access_token"] = refreshed["access_token"]
    token_data["token"] = refreshed["access_token"]
    expires_in = int(refreshed.get("expires_in", 3600))
    token_data["expiry"] = (datetime.now(tz=KST) + timedelta(seconds=expires_in)).isoformat()
    GOOGLE_TOKEN_PATH.write_text(json.dumps(token_data, ensure_ascii=False), encoding="utf-8")
    return token_data


def load_google_token() -> dict:
    token_data = json.loads(GOOGLE_TOKEN_PATH.read_text(encoding="utf-8"))
    expiry = token_data.get("expiry")
    expired = True
    if expiry:
        try:
            expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            expired = datetime.now(tz=expiry_dt.tzinfo or KST) >= expiry_dt - timedelta(minutes=5)
        except ValueError:
            expired = True
    if expired:
        logger.info("Google access_token 갱신 중")
        token_data = refresh_google_access_token(token_data)
    return token_data


def build_calendar_service():
    token_data = load_google_token()
    return build("calendar", "v3", developerKey=None, credentials=None, cache_discovery=False,
                 requestBuilder=None), token_data["access_token"]


def calendar_list_events(start: datetime, end: datetime) -> List[dict]:
    _, access_token = build_calendar_service()
    headers = {"Authorization": f"Bearer {access_token}"}

    # googleapiclient에서 credentials 없이 build 시 auth header 자동 주입이 없어서 REST fallback 사용
    params = {
        "timeMin": start.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
        "timeMax": end.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    resp = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def map_email(email: str) -> Optional[str]:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT telegram_username FROM email_map WHERE lower(email)=lower(?)", (email,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def upsert_email_map(email: str, username: str) -> None:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO email_map(email, telegram_username, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
              telegram_username=excluded.telegram_username,
              created_at=excluded.created_at
            """,
            (email.strip().lower(), username.strip().lstrip("@"), datetime.now(tz=KST).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def activate_chat(chat_id: int, title: str) -> None:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO group_chats(chat_id, title, activated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
              title=excluded.title,
              activated_at=excluded.activated_at
            """,
            (chat_id, title, datetime.now(tz=KST).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def list_active_chats() -> List[int]:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT chat_id FROM group_chats")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def get_live_message(chat_id: int) -> Optional[int]:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT message_id FROM live_message WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_live_message(chat_id: int, message_id: int) -> None:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO live_message(chat_id, message_id)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
              message_id=excluded.message_id
            """,
            (chat_id, message_id),
        )
        conn.commit()
    finally:
        conn.close()


def parse_event_due(event: dict) -> datetime:
    if "dateTime" in event.get("start", {}):
        return datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00")).astimezone(KST)
    date_val = event.get("start", {}).get("date")
    if date_val:
        return datetime.fromisoformat(date_val).replace(tzinfo=KST)
    return datetime.now(tz=KST)


def assign_users(event: dict) -> List[str]:
    users = []
    for attendee in event.get("attendees", []):
        email = attendee.get("email")
        if not email:
            continue
        mapped = map_email(email)
        if mapped:
            users.append(f"@{mapped}")

    if not users:
        organizer_email = (event.get("organizer") or {}).get("email")
        if organizer_email:
            mapped = map_email(organizer_email)
            if mapped:
                users.append(f"@{mapped}")

    if not users:
        users = ["@unmapped"]
    return sorted(set(users))


def make_d_label(due: datetime, now: datetime) -> str:
    delta_days = (due.date() - now.date()).days
    if delta_days == 0:
        return "D-0"
    if delta_days > 0:
        return f"D+{delta_days}"
    return "지연"


def build_task_items(events: List[dict], now: datetime) -> Dict[str, List[TaskItem]]:
    buckets: Dict[str, List[TaskItem]] = {}
    for ev in events:
        status = ev.get("status", "confirmed")
        if status == "cancelled":
            continue
        due = parse_event_due(ev)
        users = assign_users(ev)
        summary = ev.get("summary", "(제목 없음)")
        overdue = due < now
        if "dateTime" in ev.get("start", {}):
            when_label = due.strftime("%H:%M")
        else:
            when_label = "전일" if overdue else "종일"
        d_label = make_d_label(due, now)
        item = TaskItem(
            event_id=ev.get("id", ""),
            summary=summary,
            when_label=when_label,
            due_date=due,
            overdue=overdue,
            d_label=d_label,
        )
        for user in users:
            buckets.setdefault(user, []).append(item)

    for user in buckets:
        buckets[user].sort(key=lambda x: x.due_date)
    return buckets


def render_reminder(events: List[dict], now: datetime) -> str:
    buckets = build_task_items(events, now)
    total = 0
    overdue_count = 0

    lines = [
        f"🔔 [업무 리마인더] {now.strftime('%Y-%m-%d %H:%M')} KST",
        "",
        "━━━━━━━━━━━━━━━━",
        "📋 미완료 업무",
        "━━━━━━━━━━━━━━━━",
        "",
    ]

    if not buckets:
        lines += ["오늘~7일 내 미완료 업무가 없습니다.", "", "━━━━━━━━━━━━━━━━", "총 0건 | 지연 0건"]
        return "\n".join(lines)

    for user, items in buckets.items():
        lines.append(f"👤 {user}")
        for item in items:
            total += 1
            if item.overdue:
                overdue_count += 1
                lines.append(f"  • [{item.when_label}] {item.summary} ⚠️ 지연")
            else:
                lines.append(f"  • [{item.when_label}] {item.summary} ⏰ {item.d_label}")
        lines.append("")

    lines += ["━━━━━━━━━━━━━━━━", f"총 {total}건 | 지연 {overdue_count}건"]
    return "\n".join(lines)


def parse_due_text(raw: str, now: datetime) -> Optional[str]:
    s = raw.strip()
    if not s:
        return None
    lower = s.lower()
    if lower in {"오늘", "today"}:
        return now.date().isoformat()
    if lower in {"내일", "tomorrow"}:
        return (now.date() + timedelta(days=1)).isoformat()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            parsed = datetime.strptime(s, "%Y-%m-%d").date()
            return parsed.isoformat()
        except ValueError:
            return None

    if re.fullmatch(r"\d{1,2}/\d{1,2}", s):
        try:
            month, day = map(int, s.split("/"))
            cand = date(now.year, month, day)
            if cand < now.date():
                cand = date(now.year + 1, month, day)
            return cand.isoformat()
        except ValueError:
            return None

    return None


def split_task_and_due(args: List[str], now: datetime) -> Tuple[str, Optional[str]]:
    if not args:
        return "", None
    due = parse_due_text(args[-1], now)
    if due:
        task = " ".join(args[:-1]).strip()
    else:
        task = " ".join(args).strip()
    return task, due


def get_user_open_todos(chat_id: int, user_id: int) -> List[sqlite3.Row]:
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, task, due_date, created_at, username
            FROM todos
            WHERE chat_id = ? AND user_id = ? AND done = 0
            ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id ASC
            """,
            (chat_id, user_id),
        )
        return cur.fetchall()
    finally:
        conn.close()


def due_badge(due_date: Optional[str], now: datetime) -> str:
    if not due_date:
        return ""
    due = datetime.strptime(due_date, "%Y-%m-%d").date()
    delta = (due - now.date()).days
    due_txt = due.strftime("%m/%d")
    if delta < 0:
        return f"📅 {due_txt} ❗마감초과"
    if delta == 0:
        return f"📅 {due_txt} 🔴D-day"
    if delta == 1:
        return f"📅 {due_txt} 🟡D-1"
    return f"📅 {due_txt} D-{delta}"


def render_user_todo_list(rows: List[sqlite3.Row], now: datetime, title: Optional[str] = None) -> str:
    if not rows:
        return "미완료 to-do가 없습니다."

    lines = []
    if title:
        lines.append(title)
        lines.append("")

    for idx, row in enumerate(rows, start=1):
        badge = due_badge(row["due_date"], now)
        if badge:
            lines.append(f"{idx}. {row['task']} {badge}")
        else:
            lines.append(f"{idx}. {row['task']}")
    return "\n".join(lines)


def parse_index_arg(args: List[str]) -> Optional[int]:
    if len(args) != 1:
        return None
    try:
        idx = int(args[0])
        if idx < 1:
            return None
        return idx
    except ValueError:
        return None


def get_todo_summary_for_group(chat_id: int, now: datetime) -> Dict[str, List[sqlite3.Row]]:
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, username, task, due_date
            FROM todos
            WHERE chat_id = ? AND done = 0
            ORDER BY user_id, CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id ASC
            """,
            (chat_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    buckets: Dict[str, List[sqlite3.Row]] = {}
    for row in rows:
        username = row["username"] or str(row["user_id"])
        user_label = f"@{username}"
        buckets.setdefault(user_label, []).append(row)
    return buckets


def render_group_todo_reminder(chat_id: int, now: datetime) -> Optional[str]:
    lines = []

    # ── 1. 협업 프로젝트 현황 ──
    projects = dashboard_list_projects_full("진행중")
    lines.append(f"📌 협업 프로젝트 현황 ({now.strftime('%m/%d')} 기준)")
    lines.append("─────────────────────────")
    if projects:
        for p in projects:
            name = p.get("client") or "-"
            base = p.get("next_action") or "-"
            svc  = p.get("notes") or "-"
            lines.append(f"• {name}")
            lines.append(f"  기준일: {base}  |  서비스: {svc}")
    else:
        lines.append("  진행중 프로젝트 없음")
    lines.append("")

    # ── 2. 논의중 딜 현황 ──
    deals = dashboard_list_by_category("논의중")
    lines.append(f"🤝 논의중인 딜 현황")
    lines.append("─────────────────────────")
    if deals:
        lines.append(" / ".join(deals))
    else:
        lines.append("  논의중 딜 없음")
    lines.append("")

    # ── 3. 미완료 업무 현황 ──
    buckets = get_todo_summary_for_group(chat_id, now)
    lines.append(f"📋 미완료 업무 현황 ({now.strftime('%m/%d %H:%M')} 기준)")
    lines.append("─────────────────────────")
    if buckets:
        for user, rows in buckets.items():
            lines.append(user)
            for num, row in enumerate(rows, start=1):
                badge = due_badge(row["due_date"], now)
                if badge:
                    lines.append(f"  {num}. {row['task']} {badge}")
                else:
                    lines.append(f"  {num}. {row['task']}")
            lines.append("  ↳ /done N · /del N · /due N 날짜")
            lines.append("")
    else:
        lines.append("  ✅ 미완료 업무 없음")

    return "\n".join(lines).strip()


async def refresh_live_todo(bot, chat_id: int) -> None:
    now = datetime.now(tz=KST)
    text = render_group_todo_reminder(chat_id, now)
    if text is None:
        text = "✅ 현재 미완료 업무 없음"

    msg_id = get_live_message(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
            )
            return
        except Exception as e:
            err = str(e).lower()
            if "message to edit not found" in err or "message_id_invalid" in err:
                msg = await bot.send_message(chat_id=chat_id, text=text, message_thread_id=TODO_THREAD_ID)
                set_live_message(chat_id, msg.message_id)
                return
            logger.exception("live to-do 메시지 업데이트 실패: chat_id=%s", chat_id)
            return

    msg = await bot.send_message(chat_id=chat_id, text=text, message_thread_id=TODO_THREAD_ID)
    set_live_message(chat_id, msg.message_id)


async def send_reminder_to_all(context: ContextTypes.DEFAULT_TYPE, horizon_days: int = 7) -> None:
    now = datetime.now(tz=KST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=horizon_days + 1)).replace(hour=0)

    try:
        events = calendar_list_events(start, end)
        text = render_reminder(events, now)
        chat_ids = list_active_chats()
        if not chat_ids:
            logger.info("활성화된 그룹 채팅이 없습니다.")
            return
        for chat_id in chat_ids:
            await context.bot.send_message(chat_id=chat_id, text=text, message_thread_id=GENERAL_THREAD_ID)
        logger.info("캘린더 리마인더 전송 완료: %s개 채팅", len(chat_ids))
    except HttpError:
        logger.exception("Google Calendar API 오류")
    except Exception:
        logger.exception("캘린더 리마인더 전송 실패")


async def send_todo_reminder_to_all(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        chat_ids = list_active_chats()
        if not chat_ids:
            logger.info("활성화된 그룹 채팅이 없습니다.")
            return

        for chat_id in chat_ids:
            await refresh_live_todo(context.bot, chat_id)
        logger.info("to-do 라이브 현황판 갱신 완료: %s개 채팅", len(chat_ids))
    except Exception:
        logger.exception("to-do 라이브 현황판 갱신 실패")



async def _delete_after(msg, original_msg, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await msg.delete()
        await original_msg.delete()
    except Exception:
        pass

# GC 방지용 task 보관 셋
_bg_tasks: set = set()

async def reply_and_delete(update, text: str, delay: int = 30) -> None:
    """메시지 전송 후 delay초 뒤 백그라운드 자동 삭제 (응답 즉시 반환)"""
    msg = await update.message.reply_text(text)
    t = asyncio.create_task(_delete_after(msg, update.message, delay))
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)

async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    """즉시 미완료 업무 현황 갱신"""
    await refresh_live_todo(context.bot, update.effective_chat.id)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    chat = update.effective_chat
    activate_chat(chat.id, chat.title or chat.full_name or str(chat.id))
    await reply_and_delete(update, "✅ Task34 봇 활성화 완료\n이 채팅에 정기 리마인더를 보냅니다.")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    now = datetime.now(tz=KST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    events = calendar_list_events(start, end)
    await reply_and_delete(update, render_reminder(events, now))


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    now = datetime.now(tz=KST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=8)
    events = calendar_list_events(start, end)
    await reply_and_delete(update, render_reminder(events, now))


async def cmd_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    if len(context.args) != 2:
        await reply_and_delete(update, "사용법: /map 이메일 @텔레그램아이디")
        return

    email, username = context.args
    if "@" not in email or not username.startswith("@"):
        await reply_and_delete(update, "형식 오류. 예: /map user@company.com @username")
        return

    upsert_email_map(email, username)
    await reply_and_delete(update, f"매핑 저장: {email.lower()} → {username}")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    now = datetime.now(tz=KST)
    task, due = split_task_and_due(context.args, now)
    if not task:
        await reply_and_delete(update, "사용법: /add 할일내용 [마감일]\n마감일 형식: YYYY-MM-DD | MM/DD | 오늘 | 내일")
        return

    user = update.effective_user
    chat = update.effective_chat
    username = user.username or (user.full_name or str(user.id)).replace(" ", "")

    project = detect_project(task)

    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO todos(chat_id, user_id, username, task, due_date, done, created_at, project, priority)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, 2)
            """,
            (chat.id, user.id, username, task, due, now.isoformat(), project),
        )
        todo_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    upsert_to_supabase(
        {
            "id": todo_id,
            "task": task,
            "assignee": username,
            "due_date": due,
            "done": 0,
        }
    )

    if due:
        await reply_and_delete(update, f"✅ 등록됨: {task} (마감 {datetime.strptime(due, '%Y-%m-%d').strftime('%m/%d')})")
    else:
        await reply_and_delete(update, f"✅ 등록됨: {task}")
    await refresh_live_todo(context.bot, update.effective_chat.id)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    now = datetime.now(tz=KST)
    rows = get_user_open_todos(update.effective_chat.id, update.effective_user.id)
    text = render_user_todo_list(rows, now, title="📋 내 미완료 to-do")
    await reply_and_delete(update, text)


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    idx = parse_index_arg(context.args)
    if idx is None:
        await reply_and_delete(update, "사용법: /done 번호")
        return

    rows = get_user_open_todos(update.effective_chat.id, update.effective_user.id)
    if idx > len(rows):
        await reply_and_delete(update, "해당 번호의 to-do가 없습니다. /list 로 확인해 주세요.")
        return

    target = rows[idx - 1]
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE todos SET done = 1, completed_at = datetime('now', '+9 hours') WHERE id = ?",
            (target["id"],),
        )
        conn.commit()
    finally:
        conn.close()

    mark_done_in_supabase(
        {
            "task": target["task"],
            "assignee": target["username"] if "username" in target.keys() else "",
            "due_date": target["due_date"],
        }
    )

    await reply_and_delete(update, f"✅ 완료 처리: {target['task']}")
    await refresh_live_todo(context.bot, update.effective_chat.id)


async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    idx = parse_index_arg(context.args)
    if idx is None:
        await reply_and_delete(update, "사용법: /del 번호")
        return

    rows = get_user_open_todos(update.effective_chat.id, update.effective_user.id)
    if idx > len(rows):
        await reply_and_delete(update, "해당 번호의 to-do가 없습니다. /list 로 확인해 주세요.")
        return

    target = rows[idx - 1]
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM todos WHERE id = ?", (target["id"],))
        conn.commit()
    finally:
        conn.close()

    delete_from_supabase(
        target["task"],
        target["username"] if "username" in target.keys() else "",
    )

    await reply_and_delete(update, f"🗑 삭제됨: {target['task']}")
    await refresh_live_todo(context.bot, update.effective_chat.id)


async def cmd_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return
    if len(context.args) < 2:
        await reply_and_delete(update, "사용법: /due 번호 마감일\n마감일 형식: YYYY-MM-DD | MM/DD | 오늘 | 내일 | 없음")
        return

    try:
        idx = int(context.args[0])
        if idx < 1:
            raise ValueError
    except ValueError:
        await reply_and_delete(update, "사용법: /due 번호 마감일\n번호는 1 이상의 정수여야 합니다.")
        return

    due_arg = " ".join(context.args[1:]).strip()
    if not due_arg:
        await reply_and_delete(update, "마감일을 입력해 주세요. 예: /due 2 내일")
        return

    due: Optional[str]
    if due_arg.lower() in {"없음", "none", "null", "-"}:
        due = None
    else:
        due = parse_due_text(due_arg, datetime.now(tz=KST))
        if due is None:
            await reply_and_delete(update, "마감일 형식 오류입니다. YYYY-MM-DD | MM/DD | 오늘 | 내일 | 없음")
            return

    rows = get_user_open_todos(update.effective_chat.id, update.effective_user.id)
    if idx > len(rows):
        await reply_and_delete(update, "해당 번호의 to-do가 없습니다. /list 로 확인해 주세요.")
        return

    target = rows[idx - 1]
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE todos SET due_date = ? WHERE id = ?", (due, target["id"]))
        conn.commit()
    finally:
        conn.close()

    if due:
        await reply_and_delete(update, 
            f"📅 마감일 변경: {target['task']} → {datetime.strptime(due, '%Y-%m-%d').strftime('%m/%d')}"
        )
    else:
        await reply_and_delete(update, f"📅 마감일 제거: {target['task']}")
    await refresh_live_todo(context.bot, update.effective_chat.id)


async def cmd_proj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_dashboard_thread(update):
        return
    if len(context.args) < 3:
        await reply_and_delete(update, "사용법: /proj 프로젝트명 기준일 서비스명")
        return

    keyword = context.args[0].strip()
    base_date = context.args[1].strip()
    service_name = " ".join(context.args[2:]).strip()

    row = dashboard_find_client_by_keyword(keyword)
    if not row:
        await reply_and_delete(update, f"❌ 프로젝트 없음: {keyword}")
        return

    client_id = row.get("id")
    client_name = row.get("client") or keyword
    if client_id is None or not dashboard_update_project(int(client_id), base_date, service_name):
        await reply_and_delete(update, "❌ 업데이트 실패: 잠시 후 다시 시도해 주세요")
        return

    await reply_and_delete(update, f"✅ {client_name} 업데이트: 기준일={base_date}, 서비스={service_name}")


async def cmd_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_dashboard_thread(update):
        return
    if len(context.args) < 1:
        await reply_and_delete(update, "사용법: /deal 딜명 [on|off|done]")
        return

    deal_name = context.args[0].strip()
    state = (context.args[1].strip().lower() if len(context.args) >= 2 else "on")

    if state not in {"on", "off", "done"}:
        await reply_and_delete(update, "상태는 on/off/done 중 하나여야 합니다")
        return

    if state == "on":
        ok = dashboard_upsert_deal(deal_name, "논의중")
        if ok:
            await reply_and_delete(update, f"✅ {deal_name} 논의중 추가")
        else:
            await reply_and_delete(update, "❌ 딜 추가 실패: 잠시 후 다시 시도해 주세요")
        return

    row = dashboard_find_client_by_keyword(deal_name)
    if not row:
        await reply_and_delete(update, f"❌ 프로젝트 없음: {deal_name}")
        return

    client_id = row.get("id")
    client_name = row.get("client") or deal_name
    category = "종료" if state == "off" else "진행중"
    ok = client_id is not None and dashboard_update_deal_category(int(client_id), category)
    if not ok:
        await reply_and_delete(update, "❌ 상태 변경 실패: 잠시 후 다시 시도해 주세요")
        return

    if state == "off":
        await reply_and_delete(update, f"✅ {client_name} 종료 처리")
    else:
        await reply_and_delete(update, f"✅ {client_name} 계약 성사 — 진행중으로 이동")


async def cmd_projlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_dashboard_thread(update):
        return

    clients = dashboard_list_by_category("진행중")
    if not clients:
        await reply_and_delete(update, "📌 진행중 프로젝트 없음")
        return

    lines = ["📌 진행중 프로젝트", ""]
    lines.extend([f"- {name}" for name in clients])
    await reply_and_delete(update, "\n".join(lines))


async def cmd_deallist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_dashboard_thread(update):
        return

    clients = dashboard_list_by_category("논의중")
    if not clients:
        await reply_and_delete(update, "🗂 논의중 딜 없음")
        return

    lines = ["🗂 논의중 딜", ""]
    lines.extend([f"- {name}" for name in clients])
    await reply_and_delete(update, "\n".join(lines))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    now = datetime.now(tz=KST)
    today = now.strftime("%Y-%m-%d")

    conn = db_connect()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done,
                   SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS pending
            FROM todos
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user.id),
        )
        summary = cur.fetchone()

        cur.execute(
            """
            SELECT task
            FROM todos
            WHERE chat_id = ? AND user_id = ? AND done = 1
              AND substr(COALESCE(completed_at, created_at), 1, 10) = ?
            ORDER BY COALESCE(completed_at, created_at) DESC, id DESC
            """,
            (chat_id, user.id, today),
        )
        today_done_rows = cur.fetchall()
    finally:
        conn.close()

    total = int(summary["total"] or 0)
    done = int(summary["done"] or 0)
    pending = int(summary["pending"] or 0)
    rate = (done / total * 100) if total else 0.0

    username = user.username or (user.full_name or str(user.id))
    lines = [
        f"📊 @{username} 개인 성과",
        f"- 전체: {total}",
        f"- 완료: {done}",
        f"- 미완료: {pending}",
        f"- 완료율: {rate:.1f}%",
        "",
        f"✅ 오늘 완료 ({len(today_done_rows)}건)",
    ]

    if today_done_rows:
        lines.extend([f"  • {row['task']}" for row in today_done_rows[:20]])
        if len(today_done_rows) > 20:
            lines.append(f"  • ...외 {len(today_done_rows)-20}건")
    else:
        lines.append("  • 없음")

    await reply_and_delete(update, "\n".join(lines))


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == MAIN_CHAT_ID and update.message.message_thread_id != TODO_THREAD_ID:
        return

    chat_id = update.effective_chat.id
    now = datetime.now(tz=KST)
    today = now.strftime("%Y-%m-%d")

    conn = db_connect()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id,
                   COALESCE(NULLIF(username, ''), CAST(user_id AS TEXT)) AS username,
                   COUNT(*) AS total,
                   SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done,
                   SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS pending
            FROM todos
            WHERE chat_id = ?
            GROUP BY user_id, username
            ORDER BY done DESC, total DESC, username ASC
            """,
            (chat_id,),
        )
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT COALESCE(NULLIF(username, ''), CAST(user_id AS TEXT)) AS username, task
            FROM todos
            WHERE chat_id = ? AND done = 1
              AND substr(COALESCE(completed_at, created_at), 1, 10) = ?
            ORDER BY COALESCE(completed_at, created_at) DESC, id DESC
            """,
            (chat_id, today),
        )
        today_done_rows = cur.fetchall()
    finally:
        conn.close()

    lines = ["📈 전체 담당자 성과 요약", ""]
    if not rows:
        lines.append("등록된 업무가 없습니다.")
    else:
        for row in rows:
            total = int(row["total"] or 0)
            done = int(row["done"] or 0)
            pending = int(row["pending"] or 0)
            rate = (done / total * 100) if total else 0.0
            lines.append(f"- @{row['username']}: {done}/{total} ({rate:.1f}%) · 미완료 {pending}")

    lines.extend(["", f"✅ 오늘 완료 업무 ({len(today_done_rows)}건)"])
    if today_done_rows:
        for row in today_done_rows[:30]:
            lines.append(f"  • @{row['username']}: {row['task']}")
        if len(today_done_rows) > 30:
            lines.append(f"  • ...외 {len(today_done_rows)-30}건")
    else:
        lines.append("  • 없음")

    await reply_and_delete(update, "\n".join(lines), delay=45)


def next_top_of_hour(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(tz=KST)
    return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


async def post_init(app: Application) -> None:
    if app.bot_data.get("jobqueue_initialized"):
        return

    jq = app.job_queue
    if jq is None:
        logger.error("JobQueue unavailable; reminders are disabled")
        return

    # 캘린더 리마인더: 23~8시 + 9/13/17/21시 정각
    reminder_hours = [23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 17, 21]
    for hour in reminder_hours:
        jq.run_daily(
            callback=send_reminder_to_all,
            time=time(hour=hour, minute=0, tzinfo=KST),
            name=f"calendar-reminder-{hour:02d}",
        )

    next_hour = next_top_of_hour()
    # to-do 리마인더: 매시간 정각
    jq.run_repeating(
        callback=send_todo_reminder_to_all,
        interval=timedelta(hours=1),
        first=next_hour,
        name="todo-reminder-hourly",
    )

    app.bot_data["jobqueue_initialized"] = True
    logger.info("Task34 bot started - JobQueue schedules registered (todo next run: %s)", next_hour.isoformat())


async def async_main() -> None:
    init_db()
    token = get_bot_token()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("map", cmd_map))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("del", cmd_del))
    app.add_handler(CommandHandler("delete", cmd_del))
    app.add_handler(CommandHandler("due", cmd_due))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("proj", cmd_proj))
    app.add_handler(CommandHandler("deal", cmd_deal))
    app.add_handler(CommandHandler("projlist", cmd_projlist))
    app.add_handler(CommandHandler("deallist", cmd_deallist))

    logger.info("Task34 bot starting...")
    async with app:
        await app.start()
        await post_init(app)
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        # Run until shutdown
        import signal
        stop_event = asyncio.Event()

        def _stop():
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _stop)

        await stop_event.wait()
        await app.updater.stop()
        await app.stop()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
