#!/usr/bin/env python3
"""
Google OAuth 재인증 스크립트
──────────────────────────────────────────────
client_secret 파일(oauth-client.json)을 사용하여 Google OAuth 토큰을
갱신 또는 재발급하고 secrets/google-token.json 에 저장합니다.

사용법:
    python3 /Users/fireant/.openclaw/workspace/scripts/google_oauth_reauth.py

요구 패키지:
    pip install google-auth-oauthlib google-auth
"""

import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# ── 절대경로 하드코딩 ──────────────────────────────────────────────
CLIENT_SECRET_FILE = "/Users/fireant/.openclaw/workspace/secrets/oauth-client.json"
TOKEN_FILE = "/Users/fireant/.openclaw/workspace/secrets/google-token.json"

# ── 스코프: Spreadsheets + Calendar + Drive ────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

def main():
    # 1) client_secret 파일 존재 확인
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"❌ client_secret 파일 없음: {CLIENT_SECRET_FILE}")
        sys.exit(1)

    # 2) 기존 토큰이 있으면 refresh 시도
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"⚠️  기존 토큰 로드 실패: {e}")
            creds = None

    # 3) 유효한 토큰이면 갱신, 아니면 새 인증 플로우
    if creds and creds.valid:
        print("✅ 기존 토큰이 유효합니다.")
    elif creds and creds.refresh_token:
        from google.auth.transport.requests import Request
        print("🔄 토큰 갱신 중...")
        creds.refresh(Request())
        print("✅ 토큰 갱신 완료")
    else:
        print("🔐 새 OAuth 인증을 시작합니다 (브라우저가 열립니다)...")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
        )
        creds = flow.run_local_server(port=9753, open_browser=True)
        print("✅ OAuth 인증 완료")

    # 4) 토큰 저장
    token_dir = os.path.dirname(TOKEN_FILE)
    os.makedirs(token_dir, exist_ok=True)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_FILE, 0o600)

    # 5) 결과 출력
    print(f"💾 토큰 저장: {TOKEN_FILE}")
    print(f"   client_id : {creds.client_id}")
    print(f"   만료      : {creds.expiry}")
    print(f"   스코프    : {SCOPES}")

if __name__ == "__main__":
    main()
