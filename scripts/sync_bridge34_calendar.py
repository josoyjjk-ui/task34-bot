#!/usr/bin/env python3
"""Bridge34 팀 캘린더 → Supabase events 동기화"""
import json, uuid, urllib.request
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SUPABASE_URL = 'https://npdzxtnzjkdzwbpphduf.supabase.co'
SUPABASE_KEY = 'sb_publishable_-TVlChpvyWRZEweQ8wHe2g_WxQD5nql'
TOKEN_PATH = '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json'
SKIP_CALENDARS = ['holiday']

def get_creds():
    with open(TOKEN_PATH) as f:
        d = json.load(f)
    creds = Credentials(
        token=d.get('token'),
        refresh_token=d.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=d.get('client_id'),
        client_secret=d.get('client_secret'),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        d['token'] = creds.token
        with open(TOKEN_PATH, 'w') as f:
            json.dump(d, f)
    return creds

def sb_headers():
    return {
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Prefer': 'resolution=ignore-duplicates,return=representation'
    }

def fetch_events(days_ahead=7):
    creds = get_creds()
    service = build('calendar', 'v3', credentials=creds)
    cals = service.calendarList().list().execute()

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now + timedelta(days=days_ahead)

    all_events = []
    for c in cals['items']:
        if any(s in c['id'] for s in SKIP_CALENDARS):
            continue
        events = service.events().list(
            calendarId=c['id'],
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date'))
            end_t = e['end'].get('dateTime', e['end'].get('date', ''))
            all_events.append({
                'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, e.get('summary','') + start)),
                'summary': e.get('summary', ''),
                'start_time': start[:19].replace('T', 'T'),
                'end_time': end_t[:19] if end_t else None,
                'calendar_email': c['id'],
                'description': e.get('description', '') or '',
                'meet_link': e.get('hangoutLink') or e.get('location') or None,
            })
    return all_events

def deduplicate(events):
    """summary + start_time(분 단위) 기준으로 중복 제거 — 첫 번째만 유지"""
    seen = {}
    result = []
    for e in events:
        key = (e['summary'].strip(), e['start_time'][:16])
        if key not in seen:
            seen[key] = True
            result.append(e)
    return result

def upsert_events(events):
    if not events:
        return 0
    events = deduplicate(events)
    payload = json.dumps(events).encode()
    req = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/events',
        data=payload,
        headers=sb_headers(),
        method='POST'
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        return len(result)

if __name__ == '__main__':
    events = fetch_events(days_ahead=7)
    inserted = upsert_events(events)
    print(f"✅ 동기화 완료: {inserted}개 반영 (조회 {len(events)}개)")
    for e in sorted(events, key=lambda x: x['start_time'])[:10]:
        print(f"  {e['start_time']} | {e['summary']} [{e['calendar_email'].split('@')[0]}]")
