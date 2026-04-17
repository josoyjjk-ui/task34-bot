# AI 에이전트 보고 글자수/요약 제한 규칙 검색 결과

## 검색 대상 파일

| 파일 | 경로 | 비고 |
|------|------|------|
| AGENTS.md (루트) | `AGENTS.md` | 메인 에이전트 설정 |
| AGENTS.md (대시보드) | `fireant-dashboard/AGENTS.md` | 대시보드 에이전트 |
| AGENTS.md (inspector) | `inspector/AGENTS.md` | 검수 에이전트 |
| AGENTS.md (adjutant) | `adjutant/AGENTS.md` | 참모 에이전트 |
| AGENTS.md (ops) | `ops/AGENTS.md` | 운영 에이전트 |
| AGENTS.md (chammo) | `chammo/AGENTS.md` | 참모2 에이전트 |

> `.cursorrules`, `.clauderules`, `INSTRUCTIONS.md` 파일은 워크스페이스에 존재하지 않음.

---

## 키워드 매칭 결과

### 🔑 "3줄" / "최대 3줄"

**파일: `AGENTS.md` (루트)**

| 라인 | 정확한 문구 |
|------|------------|
| L35 | `- 보고는 최대 3줄. 핵심 결과만. 과정/코드/파일목록 나열 금지.` |
| L73 | `- 보고는 최대 3줄. 핵심 결과만.` |
| L399 | `- 백그라운드 실행 → 즉시 대화 가능 복귀 → 완료 시 3줄 이내 보고` |

**컨텍스트 (L30-42):**
```
## ⚠️ 절대 규칙 #0 — 완료보고 (모든 규칙 위에 있다)

- 작업 완료/실패 시 반드시 즉시 보고. 유저가 먼저 "?" 물어보면 규칙 위반.
- 보고는 최대 3줄. 핵심 결과만. 과정/코드/파일목록 나열 금지.
- 하네스 원문(plan ID, task results, Summary, Files changed, Tests run, Warnings) 복사 금지. 국문 요약만.
- 보고 형식: ✅ [한줄 요약] / 🔗 [링크 있으면]
- 실패 시: ❌ [원인 1줄] / 다음 조치 1줄
```

**컨텍스트 (L68-80):**
```
## 보고 규칙

### 길이 제한 (절대)
- 보고는 최대 3줄. 핵심 결과만.
- 하네스 완료 보고: 1~2줄 요약 + 링크
- 에러 보고: 원인 1줄 + 다음 조치 1줄

### 금지 항목
- 영어 원문 (Summary, Files changed, Tests run, Warnings, Checkpoint 등)
- 코드 덤프, 스크립트 전문, 파일 목록 나열
- plan ID, task ID, session ID 등 시스템 식별자
```

**컨텍스트 (L395-402):**
```
### harness_execute 호출 시
- request에 완료 기준 명확히 작성. workdir: /Users/fireant/.openclaw/workspace
- 백그라운드 실행 → 즉시 대화 가능 복귀 → 완료 시 3줄 이내 보고
```

---

### 🔑 "길이" / "길이 제한"

**파일: `AGENTS.md` (루트)**

| 라인 | 정확한 문구 |
|------|------------|
| L72 | `### 길이 제한 (절대)` |
| L283 | `- 메시지 길이: 4096자 제한 (초과 시 분할)` |

**컨텍스트 (L72-74):**
```
### 길이 제한 (절대)
- 보고는 최대 3줄. 핵심 결과만.
- 하네스 완료 보고: 1~2줄 요약 + 링크
```

**컨텍스트 (L279-285):**
```
### 텔레그램 제한사항
- 메시지 길이: 4096자 제한 (초과 시 분할)
- 이미지: 10MB 이하
- 파일: 50MB 이하
```

---

### 🔑 "요약"

**파일: `AGENTS.md` (루트)**

| 라인 | 정확한 문구 |
|------|------------|
| L14 | `- 리서치 (웹 검색, 데이터 수집, 시황 분석, 뉴스 요약)` |
| L36 | `- 하네스 원문(plan ID, task results, Summary, Files changed, Tests run, Warnings) 복사 금지. 국문 요약만.` |
| L37 | `- 보고 형식: ✅ [한줄 요약] / 🔗 [링크 있으면]` |
| L74 | `- 하네스 완료 보고: 1~2줄 요약 + 링크` |
| L191 | `- URL 요약 → web_fetch` |
| L296 | `- 일일시황: 5개 섹션 (ETF 유출입, OI 추이, DAT 추이, CB 프리미엄, 요약)` |

**파일: `fireant-dashboard/AGENTS.md`**

| 라인 | 정확한 문구 |
|------|------------|
| L69 | `- WAITING 항목은 한 줄 요약만.` |
| L203 | `**위임 임계값**: 도구 호출 3회 이상 예상되면 spawn. 결과는 요약으로 수신.` |
| L213 | `- URL 요약 → summarize 스킬` |

---

### 🔑 "limit" (보고 규칙 관련)

**파일: `inspector/AGENTS.md`, `adjutant/AGENTS.md`, `ops/AGENTS.md`, `chammo/AGENTS.md`**

| 라인 | 정확한 문구 |
|------|------------|
| L41 | `- **Memory is limited** — if you want to remember something, WRITE IT TO A FILE` |
| L135 | `You are free to edit HEARTBEAT.md with a short checklist or reminders. Keep it small to limit token burn.` |

> ※ 이 파일들의 "limit"은 보고 글자수 제한이 아닌 메모리/토큰 제한 관련 내용입니다.

---

### 🔑 "글자수", "character", "word count", "truncate", "shorten", "condensed", "brief", "분량"

| 키워드 | 결과 |
|--------|------|
| 글자수 | **해당 규칙 없음** |
| character | **해당 규칙 없음** |
| word count | **해당 규칙 없음** |
| truncate | **해당 규칙 없음** |
| shorten | **해당 규칙 없음** |
| condensed | **해당 규칙 없음** |
| brief | **해당 규칙 없음** |
| 분량 | **해당 규칙 없음** |

---

## 핵심 발견 요약

### 메인 에이전트(루트 AGENTS.md)의 보고 글자수/요약 규칙

1. **절대 규칙 #0 — 완료보고 (L30-42):**
   - 보고는 **최대 3줄**, 핵심 결과만
   - 하네스 원문(영문) 복사 금지, **국문 요약만**
   - 보고 형식: `✅ [한줄 요약] / 🔗 [링크 있으면]`
   - 실패 시: `❌ [원인 1줄] / 다음 조치 1줄`

2. **보고 규칙 > 길이 제한 (절대) (L72-74):**
   - 보고는 **최대 3줄**, 핵심 결과만
   - 하네스 완료 보고: **1~2줄 요약 + 링크**
   - 에러 보고: 원인 1줄 + 다음 조치 1줄

3. **금지 항목 (L76-79):**
   - 영어 원문 (Summary, Files changed, Tests run, Warnings 등) 금지
   - 코드 덤프, 스크립트 전문, 파일 목록 나열 금지
   - plan ID, task ID, session ID 등 시스템 식별자 금지

4. **백그라운드 작업 (L399):**
   - 완료 시 **3줄 이내 보고**

5. **텔레그램 제한 (L283):**
   - 메시지 길이: **4096자 제한** (초과 시 분할)

### 대시보드 에이전트(fireant-dashboard/AGENTS.md)

- WAITING 항목은 **한 줄 요약만** (L69)
- 위임 결과는 **요약으로 수신** (L203)
