# 🔒 민감 정보 노출 전수 검사 보고서

**대상:** GitHub 공개 저장소 `josoyjjk-ui`
**검사 일시:** 2026-04-13
**검사 대상 repo:** 4개 (fireant-dashboard, hani-kong, choaeong, fireboard)

---

## 1. 공개 Repo 목록

| # | Repo | 공개 여부 | 최종 업데이트 |
|---|------|-----------|--------------|
| 1 | josoyjjk-ui/fireant-dashboard | ✅ public | 2026-04-13 |
| 2 | josoyjjk-ui/hani-kong | ✅ public | 2026-03-20 |
| 3 | josoyjjk-ui/choaeong | ✅ public | 2026-03-19 |
| 4 | josoyjjk-ui/fireboard | ✅ public | 2026-01-22 |

---

## 2. 민감 파일 커밋 히스토리 검사 결과

### 🔴 fireant-dashboard — **노출 있음 (4건)**

| 파일 | 토큰 유형 | 노출된 값 (앞4자리+마스킹) | 최초 노출 커밋 |
|------|----------|--------------------------|---------------|
| `bots/referral-bot/export_leaderboard.py` | Telegram Bot Token | `8590****Co` (전체: 8590572213:AAFP...PCo) | `bed03e34` |
| `scripts/refresh_codex_token_v2.py` | Telegram Bot Token | `8590****Co` (동일 토큰) | `6c7d022a` |
| `giyulbot.py` | Telegram Bot Token | `8610****R4` (전체: 8610472582:AAFO...0R4) | `a8c92d88` |
| `check_members.py` | Telegram Bot Token | `8270****VxE` (전체: 8270734691:AAEu...VxE) | `ed94084b` |

**노출된 Telegram Bot 토큰 상세:**

1. **`BOT_TOKEN = "8590572213:AAFP_5xk...PCo"`** (2개 파일에 중복 노출)
   - 파일: `bots/referral-bot/export_leaderboard.py:5`
   - 파일: `scripts/refresh_codex_token_v2.py:22`

2. **`BOT_TOKEN = "8610472582:AAFO...0R4"`**
   - 파일: `giyulbot.py:20`

3. **`BOT_TOKEN = "8270734691:AAEu...VxE"`**
   - 파일: `check_members.py:6`

**기타 발견 사항:**
- OpenAI Codex OAuth Client ID (`app_EMoamEEZ73f0CkXaXp7hrann`) — refresh_codex_token_v2.py에 하드코딩 (Client ID는 공개 가능 값이나 보안 권고사항)
- Google OAuth token_path (로컬 경로만 참조, 실제 시크릿 값은 포함되지 않음)

### ✅ hani-kong — **노출 없음**

- `.env`, `.key`, `.pem`, `.secret`, `credentials.json`, `auth.json`, `config.json` 파일 커밋 히스토리에 없음
- 하드코딩 API 키 패턴 검색 결과 없음

### ✅ choaeong — **노출 없음**

- `.env`, `.key`, `.pem`, `.secret`, `credentials.json`, `auth.json`, `config.json` 파일 커밋 히스토리에 없음
- 하드코딩 API 키 패턴 검색 결과 없음

### ✅ fireboard — **노출 없음**

- `tsconfig.json`만 매칭 (민감 정보 아님)
- 하드코딩 API 키 패턴 검색 결과 없음

---

## 3. 하드코딩 API 키 패턴 검사 결과

| 패턴 | 대상 | 결과 |
|------|------|------|
| `sk-` (OpenAI) | 전체 4개 repo | 노출 없음 (node_modules 제외) |
| `AIza` (Google API) | 전체 4개 repo | 노출 없음 |
| `ghp_` / `gho_` / `github_pat_` (GitHub) | 전체 4개 repo | 노출 없음 |
| `xox[bpas]-` (Slack) | 전체 4개 repo | 노출 없음 |
| `[0-9]{10,}:[A-Za-z0-9_-]{35}` (Telegram Bot) | fireant-dashboard | **🚨 4건 노출** (위 표 참조) |
| `AKIA[0-9A-Z]{16}` (AWS) | 전체 4개 repo | 노출 없음 |

---

## 4. .gitignore 현황

| Repo | .gitignore 존재 | .env 포함 | *.key 포함 | *.pem 포함 | credentials 포함 |
|------|----------------|-----------|------------|------------|-----------------|
| fireant-dashboard | ✅ 있음 | ❌ 미포함 | ❌ 미포함 | ❌ 미포함 | ❌ 미포함 |
| hani-kong | ❌ 없음 | — | — | — | — |
| choaeong | ❌ 없음 | — | — | — | — |
| fireboard | ❌ 없음 | — | — | — | — |

**fireant-dashboard .gitignore 내용:**
```
venv/
__pycache__/
*.pyc
node_modules/
.DS_Store
*.log
secrets/
```
→ `secrets/` 디렉토리는 제외되어 있으나, `.env`, `*.key`, `*.pem`, `*credentials*` 패턴이 누락됨

---

## 5. 권장 조치 사항

### 🚨 즉시 조치 (긴급)

1. **Telegram Bot 토큰 즉시 폐기/재발급**
   - `@BotFather`에서 해당 3개 봇 토큰 모두 revoke 후 재발급
   - 기존 토큰: `8590...PCo`, `8610...R4`, `8270...VxE`

2. **커밋 히스토리에서 토큰 제거**
   - `git filter-repo` 또는 BFG Repo Cleaner로 과거 커밋에서 토큰 문자열 제거
   - 또는 `git rebase -i` 후 force push

### 📋 예방 조치

3. **.gitignore 보강** (fireant-dashboard)
   ```
   .env
   .env.*
   *.key
   *.pem
   *.secret
   *credentials*
   *auth.json
   ```

4. **.gitignore 생성** (hani-kong, choaeong, fireboard)
   - 최소한 `.env`, `.env.*`, `*.key`, `*.pem` 패턴 포함

5. **환경변수 사용으로 전환**
   - `BOT_TOKEN` 등 모든 시크릿 값을 환경변수 또는 Keychain에서 로드하도록 코드 수정
