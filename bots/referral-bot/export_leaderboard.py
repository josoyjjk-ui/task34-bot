# DB에서 leaderboard.json 생성 후 fireant-dashboard submodule에 복사 + git push
import sqlite3, json, subprocess, urllib.request
from datetime import datetime, date

BOT_TOKEN = "8590572213:AAFP_5xkCqgh2zhK_iPx3KD9C9mLnGSgPCo"
CHAT_ID = "477743685"

def tg_alert(msg: str):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": msg}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

DB = '/Users/fireant/.openclaw/workspace/bots/referral-bot/referral.db'
DASHBOARD = '/Users/fireant/.openclaw/workspace/fireant-dashboard'

# ── 이벤트 기간 체크 ──────────────────────────────────────────
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

period = None
try:
    period = con.execute("SELECT start_date, end_date FROM event_period WHERE id=1").fetchone()
except Exception:
    pass

if period:
    today = date.today()
    start = date.fromisoformat(period["start_date"])
    end   = date.fromisoformat(period["end_date"])
    if not (start <= today <= end):
        print(f"⏸ 이벤트 기간 외 ({period['start_date']} ~ {period['end_date']}), 종료.")
        con.close()
        exit(0)
else:
    print("⚠️ event_period 없음 — 기간 체크 스킵, 계속 진행.")

# ── 백업 시트에서 Eigen 이벤트 실제 참여자 전체 로드 ──────────
sheet_entries = []

# 토큰 우선순위: bridge34 → josoyjjk → 실패시 DB fallback
GSHEETS_SHEET_ID = '1prtoKycManbOj-HoMnzZ68kl6VEEm3h5vvvTUzK6QHs'
GSHEETS_SCOPES   = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_CANDIDATES = [
    '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json',
    '/Users/fireant/.openclaw/workspace/secrets/google-token.json',
    '/Users/fireant/.openclaw/workspace/secrets/google-josoyjjk-token.json',
]

sheet_loaded = False
for token_path in TOKEN_CANDIDATES:
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build as gbuild
        gcreds = Credentials.from_authorized_user_file(token_path, GSHEETS_SCOPES)
        if gcreds.expired and gcreds.refresh_token:
            gcreds.refresh(Request())
        gsvc = gbuild('sheets', 'v4', credentials=gcreds)
        gresult = gsvc.spreadsheets().values().get(
            spreadsheetId=GSHEETS_SHEET_ID, range='Sheet1!A:J'
        ).execute()
        seen = set()
        for r in gresult.get('values', [])[1:]:  # 헤더 제외
            if len(r) < 2:
                continue
            try:
                uid = int(r[1])
            except Exception:
                continue
            if uid in seen:
                continue
            seen.add(uid)
            tg_handle = r[2].lstrip('@') if len(r) > 2 else ''
            fname = r[3] if len(r) > 3 else ''
            pts = int(r[8]) if len(r) > 8 and r[8] else 0
            submitted_at = r[0] if r else ''
            sheet_entries.append({
                'user_id': uid,
                'username': tg_handle,
                'first_name': fname,
                'points': pts,
                'submitted_at': submitted_at,
            })
        print(f"📋 시트 참여 확인자: {len(sheet_entries)}명 (토큰: {token_path.split('/')[-1]})")
        sheet_loaded = True
        break
    except Exception as e:
        print(f"⚠️ 토큰 {token_path.split('/')[-1]} 실패: {e}")

if not sheet_loaded:
    tg_alert("⚠️ [리더보드] 시트 토큰 전부 실패 — DB fallback 사용")

# ── DB invite_count 계산 ──────────────────────────────────────
db_invite = {r['referrer_id']: r['cnt'] for r in con.execute(
    "SELECT referrer_id, COUNT(*) as cnt FROM users WHERE referrer_id IS NOT NULL GROUP BY referrer_id"
).fetchall()}

# ── 리더보드 생성 ─────────────────────────────────────────────
if sheet_entries:
    sheet_entries.sort(key=lambda x: (-x['points'], x['submitted_at']))
    rows = []
    for i, e in enumerate(sheet_entries):
        rows.append({
            'rank': i + 1,
            'username': e['username'],
            'first_name': e['first_name'],
            'points': e['points'],
            'invite_count': max(0, (e['points'] - 10) // 10),
        })
else:
    # fallback: DB 전체 — con이 열려있음
    event_start = period["start_date"] if period else "1970-01-01"
    db_rows = con.execute("""
        SELECT ROW_NUMBER() OVER (ORDER BY points DESC, registered_at ASC) as rank,
               username, first_name, points,
               (SELECT COUNT(*) FROM users u2 WHERE u2.referrer_id = u1.user_id) as invite_count
        FROM users u1
        WHERE points > 0 AND registered_at >= ?
        ORDER BY points DESC
    """, (event_start,)).fetchall()
    rows = [dict(r) for r in db_rows]

con.close()

total_points = sum(r["points"] for r in rows)

data = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M KST"),
    "period": {"start": period["start_date"], "end": period["end_date"]} if period else {},
    "total_points": total_points,
    "leaderboard": [
        {
            "rank": r["rank"],
            "username": r["username"] or "",
            "first_name": r["first_name"] or "",
            "points": r["points"],
            "invite_count": r["invite_count"]
        } for r in rows
    ]
}

out = f"{DASHBOARD}/leaderboard.json"
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ leaderboard.json 생성 완료 ({len(data['leaderboard'])}명)")

# ── git push ──────────────────────────────────────────────────
result = subprocess.run(
    ["bash", "-c",
     f"cd {DASHBOARD} && git fetch origin && "
     f"git add leaderboard.json && "
     f"git diff --cached --quiet || git commit -m '리더보드 자동 업데이트' && "
     f"git pull --no-rebase origin main -X ours --allow-unrelated-histories 2>/dev/null; "
     f"git push origin main"],
    capture_output=True, text=True
)
print(result.stdout or "up-to-date")
if result.returncode != 0:
    err = result.stderr[:300] if result.stderr else "unknown error"
    tg_alert(f"⚠️ [리더보드 동기화 실패]\n{err}")
    print(f"ALERT SENT: {err}")
else:
    print(result.stderr[:200] if result.stderr else "")
