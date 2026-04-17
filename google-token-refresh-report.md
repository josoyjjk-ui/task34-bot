# Google OAuth 토큰 갱신 결과 보고서

**실행 일시:** 2026-04-17 16:17:57 KST  
**스크립트:** `/Users/fireant/.openclaw/workspace/scripts/refresh-google-token.sh`  
**결과:** ❌ **실패 (invalid_grant)**

---

## 실행 결과 요약

| 항목 | 내용 |
|------|------|
| HTTP 상태 코드 | 400 |
| 오류 코드 | `invalid_grant` |
| 오류 메시지 | `Token has been expired or revoked.` |
| 로그 파일 | `/Users/fireant/.openclaw/workspace/logs/google-token-refresh.log` |
| 토큰 파일 | `/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json` |

## 원인 분석

Google OAuth refresh_token이 **만료되었거나 철회(revoked)** 되었습니다.  
2026-04-15 00:48:54 KST 이후부터 동일한 오류가 지속적으로 발생하고 있습니다.

- 마지막 성공 일시: 2026-04-13 09:11:55 KST
- 최초 실패 일시: 2026-04-15 00:48:54 KST
- 연속 실패 횟수: 3회 (04-15 2회, 04-17 1회)

## 필요 조치

1. **Google OAuth 재인증 필요** — 사용자가 브라우저에서 다시 OAuth 인증 흐름을 수행하여 새로운 refresh_token을 발급받아야 합니다.
2. 새 refresh_token을 `/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json` 파일에 업데이트해야 합니다.
3. Google Cloud Console에서 OAuth 클라이언트 설정 상태를 확인하세요 (client_id: `792432921141-k493abeg7aoqc4mklnh01775unvmudeq.apps.googleusercontent.com`).

## 로그 이력

```
[2026-04-13 09:11:55 KST] ✅ 갱신 완료 — 만료: 2026-04-13T01:11:54.219052+00:00
[2026-04-15 00:48:54 KST] ❌ 갱신 실패 [400]: invalid_grant
[2026-04-15 00:59:38 KST] ❌ 갱신 실패 [400]: invalid_grant
[2026-04-17 16:17:57 KST] ❌ 갱신 실패 [400]: invalid_grant
```

---
*이 보고서는 refresh-google-token.sh 실행 결과에 의해 자동 생성되었습니다.*
