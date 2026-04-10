#!/bin/bash
# Google OAuth 토큰 자동 갱신 스크립트
# fireant@bridge34.com

TOKEN_FILE="/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json"
LOG_FILE="/Users/fireant/.openclaw/workspace/logs/google-token-refresh.log"
mkdir -p "$(dirname "$LOG_FILE")"

python3 << 'PYEOF'
import json, requests, datetime, sys, os

TOKEN_FILE = '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json'
LOG_FILE = '/Users/fireant/.openclaw/workspace/logs/google-token-refresh.log'

def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

try:
    with open(TOKEN_FILE) as f:
        td = json.load(f)

    refresh_token = td.get('refresh_token', '')
    client_id = td.get('client_id', '')
    client_secret = td.get('client_secret', '')

    if not refresh_token:
        log("❌ refresh_token 없음 — 재인증 필요")
        sys.exit(1)

    resp = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }, timeout=10)

    result = resp.json()

    if resp.status_code == 200 and result.get('access_token'):
        td['token'] = result['access_token']
        td['expiry'] = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=result.get('expires_in', 3600))).isoformat()
        # refresh_token은 새로 오면 교체, 없으면 기존 유지
        if result.get('refresh_token'):
            td['refresh_token'] = result['refresh_token']
        with open(TOKEN_FILE, 'w') as f:
            json.dump(td, f, indent=2)
        log(f"✅ 갱신 완료 — 만료: {td['expiry']}")
    else:
        log(f"❌ 갱신 실패 [{resp.status_code}]: {result}")
        sys.exit(1)

except Exception as e:
    log(f"❌ 오류: {e}")
    sys.exit(1)
PYEOF
