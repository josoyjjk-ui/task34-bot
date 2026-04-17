# 🔒 민감 정보 노출 전수 검사 — 최종 보고서

**대상:** GitHub 공개 저장소 `josoyjjk-ui`  
**검사 일시:** 2026-04-13  
**검사 대상 repo:** 4개 (fireant-dashboard, hani-kong, choaeong, fireboard)  
**검사 도구:** grep -rn (작업 트리), git log -p (전체 커밋 히스토리 7,492개)

---

## 1. 공개 Repo 목록

| # | Repo | 공개 여부 | 최종 업데이트 |
|---|------|-----------|--------------|
| 1 | josoyjjk-ui/fireant-dashboard | ✅ public | 2026-04-13 |
| 2 | josoyjjk-ui/hani-kong | ✅ public | 2026-03-20 |
| 3 | josoyjjk-ui/choaeong | ✅ public | 2026-03-19 |
| 4 | josoyjjk-ui/fireboard | ✅ public | 2026-01-22 |

---

## 2. 하드코딩 API 키 패턴 검사 결과 (6개 패턴)

| 패턴 | 정규식 | fireant-dashboard | hani-kong | choaeong | fireboard |
|------|--------|:-:|:-:|:-:|:-:|
| OpenAI | `sk-` | 노출 없음 | 노출 없음 | 노출 없음 | 노출 없음 |
| Google API | `AIza` | 노출 없음 | 노출 없음 | 노출 없음 | 노출 없음 |
| GitHub | `ghp_\|gho_\|github_pat_` | 노출 없음 | 노출 없음 | 노출 없음 | 노출 없음 |
| Slack | `xox[bpas]-` | 노출 없음 | 노출 없음 | 노출 없음 | 노출 없음 |
| Telegram Bot | `[0-9]{10,}:[A-Za-z0-9_-]{35}` | 🚨 **4건** | 노출 없음 | 노출 없음 | 노출 없음 |
| AWS | `AKIA[0-9A-Z]{16}` | 노출 없음 | 노출 없음 | 노출 없음 | 노출 없음 |

---

## 3. 노출된 키 상세 정보

### 🔴 fireant-dashboard — **Telegram Bot Token 3종 4건 노출**

| # | 토큰 유형 | 마스킹된 값 | 파일 경로 | 라인 | 최초 노출 커밋 | 커밋 메시지 |
|---|----------|------------|----------|------|--------------|------------|
| 1 | Telegram Bot Token | `8590****PCo` | `bots/referral-bot/export_leaderboard.py` | 5 | `94dccc95` | feat: 자동화 실패 텔레그램 알림 추가 |
| 2 | Telegram Bot Token | `8590****PCo` (동일) | `scripts/refresh_codex_token_v2.py` | 22 | `6c7d022a` | feat: Codex 토큰 자동갱신 스크립트 v2 |
| 3 | Telegram Bot Token | `8610****0R4` | `giyulbot.py` | 20 | `a8c92d88` | feat: 기율봇 CS 텔레그램 봇 추가 |
| 4 | Telegram Bot Token | `8270****VxE` | `check_members.py` | 6 | `ed94084b` | 2026-02-28: fireantagent_bot 세팅 |

**노출된 토큰 상세:**
1. **`BOT_TOKEN = "8590...PCo"`** — 2개 파일에 걸쳐 중복 노출
   - 커밋 히스토리: `94dccc95` → `b0b2212e` → `6c7d022a` (3개 커밋에 걸쳐 존재)
2. **`BOT_TOKEN = "8610...0R4"`** — 1개 파일
   - 커밋 히스토리: `a8c92d88` (최초 도입)
3. **`BOT_TOKEN = "8270...VxE"`** — 1개 파일
   - 커밋 히스토리: `ed94084b` (최초 도입)

### ✅ hani-kong — **노출 없음**
### ✅ choaeong — **노출 없음**
### ✅ fireboard — **노출 없음**

---

## 4. 민감 파일 커밋 히스토리 검사

`git log --all -p` 로 검색한 결과:
- `.env`, `.env.local`, `.env.production` → 4개 repo 모두 **노출 없음**
- `config.json`, `credentials.json`, `auth.json` → 4개 repo 모두 **노출 없음**
- `*.key`, `*.pem`, `*.secret` 파일 → 4개 repo 모두 **노출 없음**
- 위 민감 파일 자체가 커밋된 기록 없음

---

## 5. .gitignore 현황

| Repo | .gitignore 존재 | .env | .env.* | *.key | *.pem | *.secret | credentials* | auth*.json | config*.json | config*.yaml |
|------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| fireant-dashboard | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| hani-kong | ❌ | — | — | — | — | — | — | — | — | — |
| choaeong | ❌ | — | — | — | — | — | — | — | — | — |
| fireboard | ❌ | — | — | — | — | — | — | — | — |

**fireant-dashboard .gitignore 현재 내용:**
```
venv/
__pycache__/
*.pyc
node_modules/
.DS_Store
*.log
secrets/
```

**누락 패턴 (fireant-dashboard):** `.env`, `.env.*`, `*.key`, `*.pem`, `*.secret`, `*credentials*`, `*auth*.json`, `*config*.json`, `*config*.yaml` (9개 패턴 전부 누락)

**누락 패턴 (hani-kong, choaeong, fireboard):** `.gitignore` 자체가 없어 모든 패턴 누락

---

## 6. 최종 요약

| 항목 | 결과 |
|------|------|
| **총 검사 repo** | 4개 |
| **총 검사 커밋** | 7,492개 (fireant-dashboard 단독) |
| **총 노출 건수** | **4건** (Telegram Bot Token 3종, fireant-dashboard에 집중) |
| **OpenAI 키** | 노출 없음 |
| **Google API 키** | 노출 없음 |
| **GitHub 토큰** | 노출 없음 |
| **Slack 토큰** | 노출 없음 |
| **AWS 키** | 노출 없음 |
| **Telegram Bot 토큰** | 🚨 **4건 노출** (3종 토큰) |

---

## 7. 권장 조치 사항

### 🚨 즉시 조치 (긴급)

1. **Telegram Bot 토큰 즉시 폐기/재발급**
   - `@BotFather`에서 해당 3개 봇 토큰 모두 revoke 후 재발급
   - 기존 토큰: `8590...PCo`, `8610...0R4`, `8270...VxE`

2. **커밋 히스토리에서 토큰 제거**
   - `git filter-repo` 또는 BFG Repo Cleaner로 과거 커밋에서 토큰 문자열 제거
   - 제거 후 force push

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
   config.json
   config.yaml
   ```

4. **.gitignore 생성** (hani-kong, choaeong, fireboard)
   ```gitignore
   .env
   .env.*
   *.key
   *.pem
   *.secret
   *credentials*
   *auth.json
   .DS_Store
   node_modules/
   ```

5. **환경변수 사용으로 전환**
   - `BOT_TOKEN` 등 모든 시크릿 값을 `os.environ.get('BOT_TOKEN')` 또는 `.env` 파일 + `python-dotenv` 로 로드
   - `.env` 파일은 절대 커밋하지 않음

6. **GitHub Secrets / push protection 활성화**
   - GitHub의 secret scanning 및 push protection 기능 활성화
