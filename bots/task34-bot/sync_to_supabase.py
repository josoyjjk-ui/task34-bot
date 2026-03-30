#!/usr/bin/env python3
"""SQLite todos -> Supabase tasks 전체 동기화 스크립트.

전략:
1) Supabase tasks 전체 삭제
2) SQLite 미완료(todo.done=0) 전체 조회
3) Supabase tasks 배치 INSERT
4) 최종 건수 확인
"""

import json
import sqlite3
from pathlib import Path

import requests

SUPABASE_URL = "https://npdzxtnzjkdzwbpphduf.supabase.co"
SUPABASE_KEY = "sb_publishable_-TVlChpvyWRZEweQ8wHe2g_WxQD5nql"
DB_PATH = Path(__file__).resolve().parent / "task34.db"


def headers(prefer_return: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    if prefer_return:
        h["Prefer"] = "return=representation"
    return h


def fetch_open_todos() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username, task, due_date
            FROM todos
            WHERE done = 0
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()
        return [
            {
                "assignee": (r["username"] or "").strip() or None,
                "task": r["task"],
                "status": "To-Do",
                "due_date": r["due_date"],
            }
            for r in rows
            if r["task"]
        ]
    finally:
        conn.close()


def delete_all_tasks() -> None:
    url = (
        f"{SUPABASE_URL}/rest/v1/tasks?"
        "id=neq.00000000-0000-0000-0000-000000000000"
    )
    resp = requests.delete(url, headers=headers(), timeout=30)
    if not resp.ok:
        raise RuntimeError(f"DELETE failed: {resp.status_code} {resp.text}")


def insert_batches(rows: list[dict], batch_size: int = 500) -> int:
    if not rows:
        return 0
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/tasks",
            headers=headers(prefer_return=True),
            data=json.dumps(batch, ensure_ascii=False),
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"INSERT failed: {resp.status_code} {resp.text}")
        total += len(batch)
    return total


def count_supabase_tasks() -> int:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/tasks?select=id",
        headers=headers(),
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"COUNT failed: {resp.status_code} {resp.text}")
    return len(resp.json())


def main() -> None:
    todos = fetch_open_todos()
    print(f"[1/4] SQLite open todos: {len(todos)}")

    delete_all_tasks()
    print("[2/4] Supabase tasks: deleted all")

    inserted = insert_batches(todos)
    print(f"[3/4] Supabase tasks: inserted {inserted}")

    final_count = count_supabase_tasks()
    print(f"[4/4] Supabase tasks final count: {final_count}")


if __name__ == "__main__":
    main()
