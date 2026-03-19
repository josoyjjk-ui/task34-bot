# CREDENTIAL-INDEX.md

| Service | Account | Label | Notes |
|---------|---------|-------|-------|
| Anthropic | openclaw | Anthropic API Key | Added 2026-02-25 |
| OpenAI | openclaw | OpenAI API Key | Added 2026-02-25 |
| xAI (Grok) | openclaw | XAI_API_KEY | Added 2026-03-19, 종량제 크레딧 |
## Google OAuth (josoyjjk@gmail.com)
- 파일: `secrets/oauth-client.json` (OAuth 클라이언트 ID)
- 토큰: `secrets/google-josoyjjk-token.json` (액세스/리프레시 토큰) ← 최신 (2026-03-20)
- 구토큰: `secrets/google-token.json` (만료됨, 스코프 부족)
- 프로젝트: fireant-workspace (792432921141)
- 스코프: gmail.send, gmail.readonly, documents, drive, spreadsheets, presentations, forms.body, forms.responses.readonly, calendar
- 인증 계정: josoyjjk@gmail.com
- 갱신: 자동 (refresh_token 사용)

## Google OAuth (fireant@bridge34.com)
- 파일: `secrets/oauth-client.json` (OAuth 클라이언트 ID)
- 토큰: `secrets/google-bridge34-token.json` (액세스/리프레시 토큰) ← 신규 (2026-03-20)
- 프로젝트: fireant-workspace (792432921141)
- 스코프: gmail.send, gmail.readonly, documents, drive, spreadsheets, presentations, forms.body, forms.responses.readonly, calendar
- 인증 계정: fireant@bridge34.com
- 갱신: 자동 (refresh_token 사용)

## Google Service Account
- 파일: `secrets/fireant-workspace-sa.json`
- 이메일: fireantagent@fireant-workspace.iam.gserviceaccount.com
- 용도: 서비스 계정 방식 (공유된 파일만 접근)
- Keychain: google-sa-fireant-workspace
