# 불개미 게시판 이벤트섹션 구현 계획서 v2

> 작성일: 2026-04-10
>
> 목적: 1차 계획서 FAIL 피드백 10개 항목을 전부 반영한 2차 실행 계획서
>
> 우선순위: 1) 로그인/인증 플로우 2) DB ERD(users 포함) 3) 보안/운영/확장

---

## 0. 문서 요약 (Executive Summary)

- 본 문서는 불개미 게시판 이벤트섹션을 "정적 이벤트 소개 페이지"에서 "인증/참여/검증/운영 가능한 이벤트 플랫폼"으로 전환하기 위한 구현안이다.
- 핵심 변경점은 다음 4가지다.
  1. Telegram Login Widget 서명검증 기반 실사용 인증 도입
  2. users/consents/audit_logs/deletion_requests 포함한 개인정보 수명주기 설계
  3. 마이그레이션 ETL(추출→정제→적재→검증→롤백) 운영 절차 문서화
  4. 운영 RBAC + 승인 워크플로우 + 비용/임계치 기반 스케일링 정책
- 아키텍처 기준은 Cloudflare (Pages + Workers + D1 + KV + R2 + Turnstile)이며, 필요시 Turso/Neon 전환 가능하도록 추상화 계층을 둔다.
- 목표 KPI는 참여율, 재참여율, 전환율이며, USP는 게시판 연계 미션/품질 점수/한국어 큐레이션/학습 아카이브다.

---

## 1. 1차 계획서 유지 요소 (좋은 부분 계승)

### 1.1 유지 원칙

- 1차 문서의 강점인 와이어프레임, 컴포넌트 트리, 기본 카드 UI, 이벤트 상세 레이아웃은 유지한다.
- 단, 인증 게이트/빈 상태/오류 상태/로딩 스켈레톤/개인정보 마스킹 컴포넌트를 추가해 운영 가능성을 높인다.
- 1차 코드 예시는 보안 결함(SQL 문자열 결합, 무인증 참여 API)을 제거하고 안전한 코드로 대체한다.

### 1.2 기존 와이어프레임(핵심 구조) 유지 + 확장

```text
메인 페이지: 히어로 배너 → 진행중 카드 → 상태 탭/검색 → 이벤트 카드 그리드 → 페이지네이션
상세 페이지: 본문(설명/체크리스트) + 사이드바(상태/보상/CTA) + 참여자 리스트 + 관련 이벤트
```

### 1.3 기존 컴포넌트 트리 유지 + 신규 컴포넌트 추가

```text
App
├── Header
├── EventListPage
│   ├── HeroBanner
│   ├── ActiveEventsSection
│   ├── FilterTabs
│   ├── SearchBar
│   ├── EventCardGrid
│   ├── Pagination
│   ├── AuthGate          # 신규
│   ├── EmptyState        # 신규
│   ├── ErrorState        # 신규
│   ├── SkeletonGrid      # 신규
│   └── PrivacyMask       # 신규
├── EventDetailPage
│   ├── EventHeader
│   ├── EventInfo
│   ├── Checklist
│   ├── EventSidebar
│   ├── ParticipantList
│   └── RelatedEvents
├── MobileBottomCTA      # 신규
└── Footer
```

---

## 2. 로그인/인증 플로우 (최우선 상세 설계)

## 2.1 요구사항 해석

- 로그인 수단: Telegram Login Widget
- 검증 방식: HMAC-SHA256 (Telegram 권장 데이터 검증)
- 세션 모델: JWT Access(15분) + Refresh(7일)
- 저장 정책: httpOnly + Secure + SameSite 쿠키
- 토큰 정책: refresh 토큰 로테이션 및 폐기(revocation)
- 필수 API: `/auth/telegram/callback`, `/auth/refresh`, `/auth/logout`

## 2.2 인증 시퀀스 다이어그램

```text
[Client] -- Telegram Widget auth data --> [POST /auth/telegram/callback]
[API] -- verify hash(HMAC-SHA256) --> [Telegram signed payload valid?]
  ├─ no: 401 + audit_logs(auth_failed)
  └─ yes: upsert users + consents
[API] -- issue tokens --> access_jwt(15m), refresh_jwt(7d,jti)
[API] -- set-cookie --> fa_access, fa_refresh (httpOnly Secure SameSite=Lax)
[Client] -- authenticated requests --> /api/* (Authorization or cookie)
[Client] -- silent renewal --> POST /auth/refresh
[API] -- rotate refresh --> revoke old jti, issue new pair
[Client] -- logout --> POST /auth/logout
[API] -- revoke current refresh family + clear cookies
```

## 2.3 Telegram 로그인 데이터 검증 로직

- 입력 필드 예시: id, first_name, last_name, username, photo_url, auth_date, hash
- 검증 절차
  1. hash 필드를 제외한 키를 사전순 정렬
  2. `key=value` 줄바꿈 문자열(data_check_string) 생성
  3. secret_key = SHA256(bot_token)
  4. computed_hash = HMAC_SHA256(secret_key, data_check_string) hex
  5. computed_hash == hash 인지 확인
  6. auth_date가 현재 대비 허용 윈도(예: 5분) 안인지 확인
- 실패 시 401 반환 + audit_logs 기록 + rate-limit 카운트 증가

## 2.4 JWT/쿠키 정책

- Access JWT
  - 만료: 15분
  - 포함 claim: sub(user_id), role, sid(session_id), iat, exp, ver(user.token_version)
- Refresh JWT
  - 만료: 7일
  - 포함 claim: sub, sid, jti, family_id, iat, exp
  - DB에 해시 저장(원문 저장 금지)
- 쿠키
  - `fa_access`: httpOnly, Secure, SameSite=Lax, Path=/
  - `fa_refresh`: httpOnly, Secure, SameSite=Strict, Path=/auth
  - 로컬 개발은 HTTPS 프록시 사용 또는 개발전용 플래그
- 로테이션
  - `/auth/refresh` 호출마다 refresh jti 신규 발급
  - 이전 jti는 revoked_at 설정
  - 재사용 감지(reuse detection) 시 family 전체 폐기

## 2.5 인증 엔드포인트 명세

### 2.5.1 POST /auth/telegram/callback

- 설명: Telegram 위젯 반환 데이터를 검증하고 로그인 세션 생성
- 인증: 없음(공개), 단 Turnstile + rate limiting 적용
- Request(JSON)
```json
{
  "id": 123456789,
  "first_name": "Hong",
  "last_name": "Gil",
  "username": "honggildong",
  "photo_url": "https://t.me/i/userpic/320/...jpg",
  "auth_date": 1760000000,
  "hash": "<telegram_hash>",
  "consent": {
    "privacyVersion": "2026-04-10",
    "termsVersion": "2026-04-10",
    "marketing": false
  },
  "source": "event_detail_cta"
}
```
- Response 200
```json
{
  "ok": true,
  "user": {
    "id": "usr_01J...",
    "telegramId": "123456789",
    "displayName": "Hong",
    "username": "honggildong",
    "role": "member"
  },
  "session": {
    "accessExpiresInSec": 900,
    "refreshExpiresInSec": 604800
  }
}
```
- 오류코드
  - 400 VALIDATION_ERROR
  - 401 INVALID_TELEGRAM_SIGNATURE
  - 401 AUTH_DATE_EXPIRED
  - 429 RATE_LIMITED

### 2.5.2 POST /auth/refresh

- 설명: refresh 토큰 검증 후 access/refresh 재발급(회전)
- 인증: `fa_refresh` 쿠키 필요
- Response 200: 새 쿠키 세트 + user summary
- 오류코드
  - 401 REFRESH_MISSING
  - 401 REFRESH_INVALID
  - 401 REFRESH_REUSED_FAMILY_REVOKED

### 2.5.3 POST /auth/logout

- 설명: 현재 세션 또는 전체 세션 로그아웃
- 인증: 로그인 필요
- Request
```json
{ "allDevices": false }
```
- 동작
  - 현재 refresh jti revoke
  - allDevices=true면 user의 active refresh family 전체 revoke
  - 쿠키 삭제
- Response 200: `{ "ok": true }`

## 2.6 인증 미들웨어 코드 예시 (TypeScript + Hono/Worker)

```ts
import { Hono } from 'hono';
import { z } from 'zod';
import { sign, verify } from 'hono/jwt';
import { getCookie, setCookie, deleteCookie } from 'hono/cookie';
import { timingSafeEqual, createHash, createHmac } from 'node:crypto';

const AccessTTL = 60 * 15;
const RefreshTTL = 60 * 60 * 24 * 7;

const TelegramPayloadSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(String),
  first_name: z.string().min(1).max(128),
  last_name: z.string().max(128).optional().default(""),
  username: z.string().max(64).optional().default(""),
  photo_url: z.string().url().optional().or(z.literal("")),
  auth_date: z.union([z.string(), z.number()]).transform((v) => Number(v)),
  hash: z.string().length(64),
  source: z.string().max(64).optional().default("unknown"),
  consent: z.object({
    privacyVersion: z.string().min(1),
    termsVersion: z.string().min(1),
    marketing: z.boolean().default(false)
  })
});

function telegramDataCheckString(input: Record<string, unknown>) {
  return Object.keys(input)
    .filter((k) => k !== 'hash' && input[k] !== undefined && input[k] !== null)
    .sort()
    .map((k) => `${k}=${String(input[k])}`)
    .join('\n');
}

function verifyTelegramSignature(payload: z.infer<typeof TelegramPayloadSchema>, botToken: string) {
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - payload.auth_date) > 300) return false;

  const secretKey = createHash('sha256').update(botToken).digest();
  const data = telegramDataCheckString(payload as unknown as Record<string, unknown>);
  const computed = createHmac('sha256', secretKey).update(data).digest('hex');

  const a = Buffer.from(computed, "hex");
  const b = Buffer.from(payload.hash, "hex");
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

const app = new Hono<{
  Bindings: {
    JWT_ACCESS_SECRET: string;
    JWT_REFRESH_SECRET: string;
    TELEGRAM_BOT_TOKEN: string;
    DB: D1Database;
  };
}>();

app.post('/auth/telegram/callback', async (c) => {
  const json = await c.req.json();
  const parsed = TelegramPayloadSchema.safeParse(json);
  if (!parsed.success) return c.json({ ok: false, error: "VALIDATION_ERROR" }, 400);

  const body = parsed.data;
  const isValid = verifyTelegramSignature(body, c.env.TELEGRAM_BOT_TOKEN);
  if (!isValid) return c.json({ ok: false, error: "INVALID_TELEGRAM_SIGNATURE" }, 401);

  const userId = crypto.randomUUID(); // 실제 구현에서는 upsert 후 기존 ID 재사용
  const sessionId = crypto.randomUUID();
  const refreshJti = crypto.randomUUID();

  const access = await sign({ sub: userId, sid: sessionId, role: "member", exp: Math.floor(Date.now()/1000) + AccessTTL }, c.env.JWT_ACCESS_SECRET);
  const refresh = await sign({ sub: userId, sid: sessionId, jti: refreshJti, family_id: refreshJti, exp: Math.floor(Date.now()/1000) + RefreshTTL }, c.env.JWT_REFRESH_SECRET);

  setCookie(c, "fa_access", access, { httpOnly: true, secure: true, sameSite: "Lax", path: "/", maxAge: AccessTTL });
  setCookie(c, "fa_refresh", refresh, { httpOnly: true, secure: true, sameSite: "Strict", path: "/auth", maxAge: RefreshTTL });

  return c.json({ ok: true, user: { id: userId, telegramId: body.id, displayName: body.first_name, username: body.username || null, role: "member" }, session: { accessExpiresInSec: AccessTTL, refreshExpiresInSec: RefreshTTL } });
});

app.post('/auth/refresh', async (c) => {
  const token = getCookie(c, "fa_refresh");
  if (!token) return c.json({ ok: false, error: "REFRESH_MISSING" }, 401);
  try {
    const payload = await verify(token, c.env.JWT_REFRESH_SECRET) as { sub: string; sid: string; jti: string; family_id: string; exp: number };
    const newJti = crypto.randomUUID();
    const access = await sign({ sub: payload.sub, sid: payload.sid, role: "member", exp: Math.floor(Date.now()/1000) + AccessTTL }, c.env.JWT_ACCESS_SECRET);
    const refresh = await sign({ sub: payload.sub, sid: payload.sid, jti: newJti, family_id: payload.family_id, exp: Math.floor(Date.now()/1000) + RefreshTTL }, c.env.JWT_REFRESH_SECRET);
    setCookie(c, "fa_access", access, { httpOnly: true, secure: true, sameSite: "Lax", path: "/", maxAge: AccessTTL });
    setCookie(c, "fa_refresh", refresh, { httpOnly: true, secure: true, sameSite: "Strict", path: "/auth", maxAge: RefreshTTL });
    return c.json({ ok: true });
  } catch {
    return c.json({ ok: false, error: "REFRESH_INVALID" }, 401);
  }
});

app.post('/auth/logout', async (c) => {
  deleteCookie(c, "fa_access", { path: "/" });
  deleteCookie(c, "fa_refresh", { path: "/auth" });
  return c.json({ ok: true });
});
```

## 2.7 인증 실패/예외 처리 정책

- Telegram hash mismatch 5회/10분 초과: IP 단위 30분 차단
- refresh 재사용 탐지: 해당 family 강제 폐기 + 사용자 재로그인 유도
- 클라이언트 시계 오차로 auth_date 실패 시, 서버시간 안내 문구 표시
- 로그아웃 성공 후 클라이언트 캐시(user/me) 강제 무효화

---

## 3. 유저 데이터 저장/ERD/개인정보 처리

## 3.1 ERD (필수 테이블 포함)

```text
users 1---n sessions
users 1---n consents
users 1---n participants
events 1---n participants
participants 1---n participant_events
participants 1---n verification_logs
users 1---n deletion_requests
users 1---n audit_logs (actor_user_id)
```

## 3.2 D1 SQL 마이그레이션 (핵심)

```sql
-- 0001_users_and_auth.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  telegram_id TEXT NOT NULL UNIQUE,
  username TEXT,
  first_name TEXT NOT NULL,
  last_name TEXT,
  photo_url TEXT,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('member','reviewer','editor','admin','owner')),
  status TEXT NOT NULL DEFAULT "active" CHECK(status IN ("active","blocked","deleted")),
  token_version INTEGER NOT NULL DEFAULT 1,
  source TEXT NOT NULL DEFAULT "telegram_widget",
  created_at TEXT NOT NULL DEFAULT (datetime("now")),
  updated_at TEXT NOT NULL DEFAULT (datetime("now")),
  deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  refresh_jti_hash TEXT NOT NULL UNIQUE,
  refresh_family_id TEXT NOT NULL,
  user_agent TEXT,
  ip_hash TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime("now")),
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  revoke_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_family ON sessions(refresh_family_id);

CREATE TABLE IF NOT EXISTS consents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  privacy_version TEXT NOT NULL,
  terms_version TEXT NOT NULL,
  marketing_opt_in INTEGER NOT NULL DEFAULT 0,
  consented_at TEXT NOT NULL DEFAULT (datetime("now")),
  source TEXT NOT NULL DEFAULT "signup"
);

CREATE INDEX IF NOT EXISTS idx_consents_user_id ON consents(user_id);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  long_description_md TEXT,
  banner_image TEXT,
  thumbnail_image TEXT,
  status TEXT NOT NULL CHECK(status IN ("draft","review","scheduled","active","ended","archived")),
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  reward_type TEXT NOT NULL DEFAULT "points",
  reward_amount INTEGER NOT NULL DEFAULT 0,
  reward_unit TEXT NOT NULL DEFAULT "P",
  source TEXT NOT NULL DEFAULT "manual",
  version INTEGER NOT NULL DEFAULT 1,
  created_by TEXT REFERENCES users(id),
  updated_by TEXT REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime("now")),
  updated_at TEXT NOT NULL DEFAULT (datetime("now")),
  deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_starts_ends ON events(starts_at, ends_at);

CREATE TABLE IF NOT EXISTS event_conditions (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id),
  sort_order INTEGER NOT NULL DEFAULT 0,
  condition_type TEXT NOT NULL,
  platform TEXT NOT NULL,
  label TEXT NOT NULL,
  target_url TEXT,
  auto_verify INTEGER NOT NULL DEFAULT 0,
  verification_method TEXT NOT NULL DEFAULT "manual",
  created_at TEXT NOT NULL DEFAULT (datetime("now")),
  updated_at TEXT NOT NULL DEFAULT (datetime("now")),
  deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS participants (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  event_id TEXT NOT NULL REFERENCES events(id),
  status TEXT NOT NULL CHECK(status IN ("in_progress","completed","disqualified","rewarded")),
  progress_json TEXT NOT NULL DEFAULT "{}",
  source TEXT NOT NULL DEFAULT "event_detail",
  idempotency_key TEXT NOT NULL,
  joined_at TEXT NOT NULL DEFAULT (datetime("now")),
  completed_at TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  deleted_at TEXT,
  UNIQUE(event_id, user_id),
  UNIQUE(idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_participants_event_status ON participants(event_id, status);

CREATE TABLE IF NOT EXISTS participant_events (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES participants(id),
  from_status TEXT,
  to_status TEXT NOT NULL,
  reason TEXT,
  actor_user_id TEXT REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime("now"))
);

CREATE INDEX IF NOT EXISTS idx_participant_events_pid ON participant_events(participant_id, created_at);

CREATE TABLE IF NOT EXISTS verification_logs (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES participants(id),
  condition_id TEXT REFERENCES event_conditions(id),
  verifier_type TEXT NOT NULL CHECK(verifier_type IN ("manual","bot","api","system")),
  result TEXT NOT NULL CHECK(result IN ("pass","fail","pending")),
  evidence_json TEXT,
  verified_by TEXT REFERENCES users(id),
  verified_at TEXT NOT NULL DEFAULT (datetime("now"))
);

CREATE TABLE IF NOT EXISTS deletion_requests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  request_channel TEXT NOT NULL,
  reason TEXT,
  status TEXT NOT NULL CHECK(status IN ("requested","approved","processing","done","rejected")),
  requested_at TEXT NOT NULL DEFAULT (datetime("now")),
  handled_by TEXT REFERENCES users(id),
  handled_at TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  actor_user_id TEXT REFERENCES users(id),
  actor_role TEXT,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  ip_hash TEXT,
  ua TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime("now"))
);

CREATE INDEX IF NOT EXISTS idx_audit_action_time ON audit_logs(action, created_at);
```

## 3.3 개인정보 처리방침(초안)

### 3.3.1 수집 항목
- 필수: telegram_id, username(선택), first_name, last_name(선택), auth_date, 참여 기록
- 선택: photo_url, 마케팅 수신동의 여부
- 보안 로그: IP 해시, User-Agent, 인증 실패 횟수, 관리자 변경 이력

### 3.3.2 처리 목적
- 로그인/본인 식별
- 이벤트 참여 관리 및 중복 방지
- 부정 참여 탐지, 보안 사고 대응
- 법적 요청 대응 및 분쟁 처리

### 3.3.3 보관 기간
- 계정 기본정보: 탈퇴 후 최대 30일 내 비식별화
- 참여/검증 기록: 운영/정산 목적상 1년 보관 후 집계만 유지
- 감사 로그(audit_logs): 1년 보관(보안사고 발생 시 연장 가능)
- 삭제 요청 이력: 처리 완료 후 1년

### 3.3.4 삭제 프로세스
- 사용자 삭제 요청 접수(deletion_requests= requested)
- 관리자 승인(approved)
- 배치 작업으로 users.status=deleted, PII 마스킹, 관련 세션 폐기
- participants는 통계 무결성 위해 user_id를 익명 대체키로 치환
- 완료(done) 후 audit_logs 기록

---

## 4. 데이터 구조 고도화 (idempotency/source/versioning/soft delete)

### 4.1 필드 설계 원칙

- idempotency_key: 참여 API 중복 제출 방지(클라이언트 UUID + eventId + userId 조합 권장)
- source: 유입경로 추적(event_list, event_detail, tg_channel, board_mission 등)
- verification_logs: 조건 검증 증거 저장(JSON)
- participant_events: 상태 이력(event-sourcing 보조 테이블)
- soft delete: deleted_at 기준 삭제 논리 처리
- version: optimistic locking과 변경 이력 기준값

### 4.2 참가 상태 전이 규칙

```text
in_progress -> completed -> rewarded
in_progress -> disqualified
completed -> disqualified (사후 위반 발견 시)
모든 전이는 participant_events에 기록해야 함
```

### 4.3 예시 쿼리 (prepared statement 사용)

```ts
// 참여 생성(멱등)
const stmt = env.DB.prepare(`
  INSERT INTO participants (id, user_id, event_id, status, source, idempotency_key)
  VALUES (?, ?, ?, ?, ?, ?)
  ON CONFLICT(idempotency_key) DO NOTHING
`);
await stmt.bind(pid, uid, eid, "in_progress", source, idem).run();

// 상태 전이 + 이력 기록은 트랜잭션으로 묶기
```

---

## 5. 마이그레이션 상세 (ETL + 매핑 + 검증 + 롤백)

## 5.1 마이그레이션 대상

- Source A: 구글폼 응답 CSV
- Source B: 텔레그램 봇 로그(JSON/SQLite)
- Target: D1 events/users/participants/verification_logs

## 5.2 ETL 단계

1. Extract: 소스 원본을 immutable snapshot으로 보관 (`/migration/snapshots/YYYYMMDD`)
2. Transform: 필드 정규화(시간대 통일, 닉네임 정리, 상태 매핑)
3. Load: staging 테이블 적재 후 본 테이블 merge
4. Validate: row count, 샘플 검증, 중복 검사, FK 무결성 검사
5. Reconcile: 누락/충돌 케이스 수동 보정
6. Promote: 검증 통과분만 production 반영

## 5.3 소스별 필드 매핑표

| Source | Source Field | Target Table.Column | Rule |
|---|---|---|---|
| Google Form | telegram_id | users.telegram_id | 문자열화 + trim |
| Google Form | nickname | users.display_name | 없으면 username 대체 |
| Google Form | event_slug | events.slug | 기존 이벤트 매핑필수 |
| Google Form | submitted_at | participants.joined_at | KST→UTC normalize |
| Telegram Bot | user.id | users.telegram_id | upsert key |
| Telegram Bot | user.username | users.username | null 허용 |
| Telegram Bot | action.join_event | participants.status | 기본 in_progress |
| Telegram Bot | verification.result | verification_logs.result | pass/fail/pending 정규화 |
| Telegram Bot | verification.payload | verification_logs.evidence_json | JSON 문자열 |

## 5.4 dedupe 키 전략

- users: telegram_id unique
- participants: unique(event_id, user_id) + unique(idempotency_key)
- verification_logs: hash(participant_id + condition_id + verified_at minute bucket)
- staging 단계에서는 duplicate bucket 생성 후 우선순위 룰 적용

## 5.5 dry-run/검증

- dry-run 모드: production write 금지, staging에만 적재
- 필수 검증
  - total rows source == (insert + update + skip_duplicate + error)
  - orphan 참가자(존재하지 않는 users/events 참조) 0건
  - 최근 30건 샘플 수작업 대조
  - 민감정보 컬럼 누락/형변환 오류 0건

## 5.6 롤백 전략

- 전략 A: migration batch_id 기반 논리 롤백(soft delete)
- 전략 B: D1 export snapshot 복원
- 전략 C: blue/green DB 전환 (규모 확대시)
- 롤백 트리거
  - 오류율 0.5% 초과
  - FK 위반 발생
  - 인증/참여 주요 API 95p latency 2배 이상 악화

### 5.7 마이그레이션 SQL 예시 (staging)

```sql
CREATE TABLE IF NOT EXISTS staging_google_form (
  batch_id TEXT NOT NULL,
  row_no INTEGER NOT NULL,
  telegram_id TEXT,
  nickname TEXT,
  event_slug TEXT,
  submitted_at TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_bot_log (
  batch_id TEXT NOT NULL,
  row_no INTEGER NOT NULL,
  telegram_id TEXT,
  username TEXT,
  action TEXT,
  result TEXT,
  event_slug TEXT,
  payload_json TEXT,
  action_at TEXT,
  raw_json TEXT NOT NULL
);
```

---

## 6. 기술 스택/부하추정/D1 임계치/캐시 전략

## 6.1 권장 스택

- Frontend: Astro + React islands
- API: Cloudflare Workers(Hono)
- DB: Cloudflare D1 (초기), scale-up 시 Turso/Neon 검토
- Cache: Cloudflare KV + CDN cache + client SWR
- Object: R2 (배너/썸네일/CSV 업로드)
- Security: Turnstile, WAF rate limiting, CSP/HSTS

## 6.2 DAU/MAU 시나리오

| 시나리오 | DAU | MAU | 일평균 API Req | 피크 RPS(예상) | D1 읽기/쓰기 비율 |
|---|---:|---:|---:|---:|---|
| Basic | 1,000 | 10,000 | 60,000 | 10~20 | 90/10 |
| Growth | 10,000 | 100,000 | 700,000 | 80~150 | 92/8 |
| Peak | 50,000 | 500,000 | 4,000,000 | 400~700 | 94/6 |

가정: 1인당 평균 6~8 API 호출/일, 이벤트 오픈 시 5배 버스트

## 6.3 D1 제한 도달 임계치(운영 판단 기준)

- 응답지연 기준: DB query p95 > 200ms 지속 15분
- 오류기준: 5xx 또는 timeout > 1%/5분
- 쓰기경합 기준: 참여 API의 conflict/retry > 3%
- 임계치 초과 시 액션
  1. KV 캐시 TTL 확대(이벤트 목록 60초→300초)
  2. hot query를 aggregate table로 분리
  3. write-heavy 테이블(participant_events) 비동기 큐 처리
  4. 필요시 read replica/외부 DB 전환 검토

## 6.4 캐시 전략

- 계층 1: CDN 캐시 (public list/detail GET)
- 계층 2: KV 캐시 (`events:list:{filter}:{page}`)
- 계층 3: 클라이언트 SWR cache
- 무효화
  - 이벤트 publish/update 시 해당 slug/list key purge
  - 참여 업데이트는 개인화 데이터로 no-store

---

## 7. 보안 설계 (취약점 개선 포함)

## 7.1 주요 취약점과 개선

- 취약점 A: SQL 문자열 삽입
  - 개선: prepared statement 강제 + lint rule
- 취약점 B: 무인증 참여 API
  - 개선: auth middleware + role check + CSRF 대응
- 취약점 C: 입력값 무검증
  - 개선: Zod 스키마 + 실패시 400

## 7.2 Zod 스키마 예시

```ts
import { z } from "zod";

export const ParticipateSchema = z.object({
  eventId: z.string().regex(/^evt_[A-Za-z0-9]+$/),
  idempotencyKey: z.string().uuid(),
  source: z.enum(["event_list","event_detail","tg_channel","board_mission"]),
  conditions: z.array(z.object({
    conditionId: z.string().min(3),
    checked: z.boolean()
  })).max(50)
});
```

## 7.3 API 엔드포인트별 권한표

| Endpoint | Method | 인증 | 권한 | 비고 |
|---|---|---|---|---|
| /auth/telegram/callback | POST | Public | Public | Turnstile 필수 |
| /auth/refresh | POST | Refresh Cookie | User | 회전 필수 |
| /auth/logout | POST | Access | User | allDevices 옵션 |
| /api/events | GET | Optional | Public | 목록 캐시 가능 |
| /api/events/:id | GET | Optional | Public | 상세 캐시 가능 |
| /api/events | POST | Access | Editor+ | draft 생성 |
| /api/events/:id/review | POST | Access | Reviewer+ | 승인 요청 |
| /api/events/:id/publish | POST | Access | Admin+ | 게시/예약 |
| /api/participate | POST | Access | Member+ | 멱등키 필수 |
| /api/admin/import/csv | POST | Access | Admin+ | CSV import |
| /api/admin/audit-logs | GET | Access | Owner/Admin | 마스킹 출력 |

## 7.4 Cloudflare 보안 설정

- WAF Rate limiting
  - /auth/*: IP당 10req/min
  - /api/participate: 사용자당 30req/min
  - /api/admin/*: IP allowlist + bot score 조건
- Turnstile
  - 로그인 콜백/회원가입 유사 엔드포인트 적용
- CSP/HSTS 헤더
```http
Content-Security-Policy: default-src "self"; img-src "self" https://t.me data:; script-src "self" https://telegram.org; frame-ancestors "none"
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 8. 와이어프레임 확장 (AuthGate/상태컴포넌트/모바일 CTA)

## 8.1 메인 화면 상태별 UI

### 8.1.1 AuthGate
```text
[비로그인]
이벤트 참여를 위해 로그인해주세요
[Telegram으로 로그인] [나중에 하기]
```

### 8.1.2 EmptyState
```text
조건에 맞는 이벤트가 없습니다
[필터 초기화]
```

### 8.1.3 ErrorState
```text
데이터를 불러오지 못했습니다
[다시 시도] [상태 페이지 보기]
```

### 8.1.4 Skeleton
```text
카드 8개 스켈레톤 + 제목/메타 라인 placeholder
```

### 8.1.5 PrivacyMask
```text
참여자 목록 닉네임: fire**** / crypto*** 형태 마스킹
```

## 8.2 모바일 하단 고정 CTA

```text
┌──────────────────────────────┐
│ [지금 참여하기]  [공유하기]  │  <- viewport 하단 고정
└──────────────────────────────┘
```

## 8.3 모바일 접근성

- CTA 버튼 높이 48px 이상
- Safe area inset 대응(iOS)
- 스크린리더 라벨 명시

---

## 9. 운영(관리자) 기능 설계

## 9.1 RBAC

| Role | 이벤트 작성 | 수정 | 리뷰 | 게시/종료 | CSV import | 롤백 | 사용자차단 |
|---|---|---|---|---|---|---|---|
| Owner | O | O | O | O | O | O | O |
| Admin | O | O | O | O | O | O | O |
| Editor | O | O | X | X | O(제한) | X | X |
| Reviewer | X | 코멘트 | O | X | X | X | X |
| Member | X | X | X | X | X | X | X |

## 9.2 승인흐름 (draft → review → publish)

```text
Editor가 draft 생성
 -> Reviewer에게 review 요청
 -> Reviewer 승인/반려
 -> Admin/Owner publish 또는 schedule
 -> active 시작
 -> ended/archived
```

## 9.3 CSV import

- 업로드 파일 검증: 헤더 필수, UTF-8, 최대 10MB
- dry-run preview: insert/update/skip/error 건수 표시
- 확정 import: batch_id 발급 + audit_logs 기록
- 실패 레코드 다운로드 제공(error_report.csv)

## 9.4 예약 게시

- scheduled 상태에서 starts_at 도달 시 active 전환 배치
- 배치 실패 시 알람(Slack/Telegram)
- 시간대는 내부 UTC 저장, 관리자 UI는 KST 표시

## 9.5 변경 이력/롤백

- events.version 증가 + event_revisions 별도 저장(확장안)
- "직전 버전으로 롤백" 원클릭 지원
- 롤백 시 audit_logs(action=event.rollback) 기록

---

## 10. 비용/스케일링 계획

## 10.1 비용표 (기본/성장/피크)

| 항목 | 기본(DAU 1k) | 성장(DAU 10k) | 피크(DAU 50k) | 비고 |
|---|---:|---:|---:|---|
| Cloudflare Pages | $0 | $20 | $50+ | 빌드 빈도 증가 시 |
| Workers | $0~5 | $30~80 | $200~500 | 요청량 의존 |
| D1 | $0~5 | $30~120 | $200~700 | read/write량 의존 |
| KV | $0~5 | $20~60 | $80~200 | 캐시 hit율 중요 |
| R2 | $0~2 | $5~30 | $30~100 | 이미지/백업 |
| Monitoring | $0~10 | $20~80 | $100~300 | 로그 보관 정책 영향 |
| 합계(대략) | $0~27 | $125~390 | $660~1,850 | 추정치 |

## 10.2 무료 한계 수치와 경고

- 무료 플랜 한계 접근 경고 기준 70%, 85%, 95%
- 알람 지표
  - 요청량/일
  - D1 쿼리 실패율
  - p95 응답시간
  - 배치 실패 횟수

## 10.3 유료 전환 조건

- 2주 연속 85% 임계치 초과
- 이벤트 오픈 당일 5xx > 0.5%
- 운영 인력이 수동 재시도에 하루 1시간 이상 소모
- 전환 우선순위: Workers → D1 → Monitoring

---

## 11. 차별점(USP) 및 KPI

## 11.1 USP 정의 (3개 이상)

1) 게시판 연계 미션
- 단순 클릭미션이 아닌 게시판 글/댓글/피드백과 연결된 참여형 미션 제공
- 예: "이번 주 분석글 1개 + 타인 글에 근거 있는 댓글 2개"

2) 댓글/콘텐츠 품질 점수
- 길이만 보는 것이 아니라 신고율, 추천/비추천, 운영자 리뷰 기반 품질 점수화
- 저품질 반복 참여자 패널티로 보상 공정성 강화

3) 한국어 커뮤니티 큐레이션
- 한국어 사용자 관점의 이벤트 선별/요약/용어 해설
- 영어 원문 이벤트를 한국어 가이드와 함께 제공

4) 지난 이벤트 학습 아카이브
- 종료 이벤트를 "무엇이 잘 됐는지"까지 저장
- 신규 사용자 온보딩에 과거 베스트 케이스 활용

## 11.2 KPI 정의

| KPI | 정의 | 목표(초기 3개월) |
|---|---|---|
| 참여율 | 이벤트 페이지 방문 대비 참여 클릭 비율 | 18%+ |
| 재참여율 | 지난 30일 참여자 중 재참여자 비율 | 35%+ |
| 전환율 | 참여 시작 대비 완료/보상 수령 비율 | 55%+ |
| 품질점수 평균 | 완료 콘텐츠 평균 품질점수 | 70점+ |
| 운영 처리시간 | 리뷰 요청→게시 승인 소요 | 24시간 이내 |

## 11.3 KPI 수집 이벤트 정의

- `event_view`
- `participate_click`
- `participate_submit`
- `condition_verified`
- `event_completed`
- `reward_claimed`
- `content_quality_scored`

---

## 12. API 상세 설계 (핵심 엔드포인트)

### 12.1 공개 API
- GET /api/events?status=&q=&page=
- GET /api/events/:id
- GET /api/events/:id/participants?status=&page=

### 12.2 인증 API
- POST /auth/telegram/callback
- POST /auth/refresh
- POST /auth/logout
- GET /auth/me

### 12.3 참여 API
- POST /api/participate
- POST /api/participants/:id/verify
- POST /api/participants/:id/status

### 12.4 관리자 API
- POST /api/admin/events
- PATCH /api/admin/events/:id
- POST /api/admin/events/:id/request-review
- POST /api/admin/events/:id/publish
- POST /api/admin/events/:id/schedule
- POST /api/admin/import/csv
- POST /api/admin/events/:id/rollback

### 12.5 /api/participate 코드 예시

```ts
app.post('/api/participate', authRequired, async (c) => {
  const body = ParticipateSchema.parse(await c.req.json());
  const user = c.get("user");

  const event = await c.env.DB.prepare(
    `SELECT id, status, starts_at, ends_at FROM events WHERE id = ? AND deleted_at IS NULL`
  ).bind(body.eventId).first();

  if (!event) return c.json({ ok: false, error: "EVENT_NOT_FOUND" }, 404);
  if (event.status !== "active") return c.json({ ok: false, error: "EVENT_NOT_ACTIVE" }, 409);

  const pid = crypto.randomUUID();
  const insert = await c.env.DB.prepare(`
    INSERT INTO participants (id, user_id, event_id, status, source, idempotency_key, progress_json)
    VALUES (?, ?, ?, "in_progress", ?, ?, ?)
    ON CONFLICT(idempotency_key) DO NOTHING
  `).bind(pid, user.id, body.eventId, body.source, body.idempotencyKey, JSON.stringify(body.conditions)).run();

  return c.json({ ok: true, affected: insert.meta.changes });
});
```

---

## 13. 프론트엔드 컴포넌트 명세 (확장판)

| 컴포넌트 | 설명 | 상태 | 비고 |
|---|---|---|---|
| AuthGate | 로그인 유도 모달/인라인 | new | Telegram Widget 연동 |
| EventCard | 이벤트 요약 카드 | keep | v1 유지 |
| EventSidebar | 참여 CTA 영역 | keep | 모바일 CTA 분리 |
| FilterTabs | 전체/진행중/종료 | keep | 카운트 배지 |
| SearchBar | 검색 입력 | keep | 디바운스 300ms |
| EmptyState | 결과 없음 안내 | new | 필터 초기화 버튼 |
| ErrorState | 오류 안내 | new | 재시도 버튼 |
| SkeletonGrid | 로딩 플레이스홀더 | new | 8~12 cards |
| PrivacyMask | 닉네임/ID 마스킹 | new | 관리자 권한 예외 |
| MobileBottomCTA | 하단 고정 CTA | new | 접근성 필수 |

### 13.1 EventCard 코드 (v1 유지 + 접근성/보안 보완)

```tsx
type EventCardProps = {
  event: {
    id: string;
    title: string;
    thumbnailImage: string;
    status: "active" | "ended" | "upcoming";
    participantCount: number;
    rewardAmount: number;
    rewardUnit: string;
    endsAt: string;
  };
};

function formatMaskCount(n: number) {
  return new Intl.NumberFormat("ko-KR").format(n);
}

export function EventCard({ event }: EventCardProps) {
  return (
    <a href={`/events/${event.id}`} className="event-card" aria-label={`${event.title} 상세보기`}>
      <img src={event.thumbnailImage} alt="" loading="lazy" />
      <h3>{event.title}</h3>
      <p>참여자 {formatMaskCount(event.participantCount)}명</p>
      <p>보상 {event.rewardAmount}{event.rewardUnit}</p>
    </a>
  );
}
```

---

## 14. 관측성/모니터링/알람

## 14.1 SLI/SLO
- Auth callback 성공률 >= 99.5%
- Participate API p95 <= 350ms
- Admin publish 작업 성공률 >= 99%

## 14.2 대시보드 지표
- 로그인 성공/실패율
- refresh 회전 성공률
- 참여 멱등 충돌률
- 이벤트 상태별 참여 전환
- 리뷰 대기시간

## 14.3 알람 룰
- auth failure rate > 5% (5분)
- 5xx > 1% (5분)
- queue backlog > 1,000
- scheduled publish 지연 > 3분

---

## 15. 릴리즈 플랜

### Phase A (1주): 인증 + 기본 이벤트 리스트
- Telegram 로그인 + /auth/*
- users/sessions/consents 테이블 도입
- 이벤트 리스트/상세 + AuthGate

### Phase B (2주): 참여 + 검증 + 관리자 기본
- participants/verification_logs/participant_events
- 참여 API 멱등키/검증 도입
- draft/review/publish

### Phase C (2주): 마이그레이션/운영 자동화/비용 최적화
- ETL 파이프라인
- CSV import + rollback
- 캐시/알람/비용 임계치 자동 경고

---

## 16. 체크리스트 (10개 피드백 반영 검증)

- [x] 1. 로그인/인증 플로우 상세(서명검증, JWT, 쿠키, 회전/폐기, /auth endpoints)
- [x] 2. users/consents/audit_logs/deletion_requests 포함 ERD 및 개인정보정책
- [x] 3. ETL 단계, 필드 매핑표, dedupe key, dry-run, 롤백
- [x] 4. DAU/MAU 부하추정(1k/10k/50k), D1 임계치, 캐시전략
- [x] 5. AuthGate/Empty/Error/Skeleton/PrivacyMask + 모바일 하단 CTA
- [x] 6. idempotency key, source, verification_logs, participant_events, soft delete, versioning
- [x] 7. Zod, prepared statement, Cloudflare rate limit/Turnstile, CSP/HSTS, 권한표
- [x] 8. 비용표(기본/성장/피크), 무료한계, 임계치 알람, 유료전환 조건
- [x] 9. RBAC, draft→review→publish, CSV import, 예약게시, 변경이력/롤백
- [x] 10. USP 3개+ 및 KPI(참여율/재참여율/전환율)

---

## 17. 부록 A. API 오류 코드 카탈로그
- E001 `VALIDATION_ERROR`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E002 `INVALID_TELEGRAM_SIGNATURE`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E003 `AUTH_DATE_EXPIRED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E004 `REFRESH_MISSING`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E005 `REFRESH_INVALID`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E006 `REFRESH_REUSED_FAMILY_REVOKED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E007 `UNAUTHORIZED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E008 `FORBIDDEN`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E009 `EVENT_NOT_FOUND`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E010 `EVENT_NOT_ACTIVE`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E011 `ALREADY_PARTICIPATED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E012 `RATE_LIMITED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E013 `TURNSTILE_FAILED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E014 `CSV_SCHEMA_INVALID`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E015 `IMPORT_DRYRUN_FAILED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E016 `ROLLBACK_REQUIRED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E017 `ROLLBACK_FAILED`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용
- E018 `INTERNAL_ERROR`: 표준 오류 응답 포맷(`ok=false,error,requestId`) 적용

## 18. 부록 B. 운영 런북 상세 체크리스트

아래 런북은 실제 운영시 사용 가능한 작업 단위로 작성했다.

- [ ] Runbook-001 (Auth): 세부 점검 항목 #1 수행 및 audit_logs 기록
- [ ] Runbook-002 (Auth): 세부 점검 항목 #2 수행 및 audit_logs 기록
- [ ] Runbook-003 (Auth): 세부 점검 항목 #3 수행 및 audit_logs 기록
- [ ] Runbook-004 (Auth): 세부 점검 항목 #4 수행 및 audit_logs 기록
- [ ] Runbook-005 (Auth): 세부 점검 항목 #5 수행 및 audit_logs 기록
- [ ] Runbook-006 (Auth): 세부 점검 항목 #6 수행 및 audit_logs 기록
- [ ] Runbook-007 (Auth): 세부 점검 항목 #7 수행 및 audit_logs 기록
- [ ] Runbook-008 (Auth): 세부 점검 항목 #8 수행 및 audit_logs 기록
- [ ] Runbook-009 (Auth): 세부 점검 항목 #9 수행 및 audit_logs 기록
- [ ] Runbook-010 (Auth): 세부 점검 항목 #10 수행 및 audit_logs 기록
- [ ] Runbook-011 (Auth): 세부 점검 항목 #11 수행 및 audit_logs 기록
- [ ] Runbook-012 (Auth): 세부 점검 항목 #12 수행 및 audit_logs 기록
- [ ] Runbook-013 (Auth): 세부 점검 항목 #13 수행 및 audit_logs 기록
- [ ] Runbook-014 (Auth): 세부 점검 항목 #14 수행 및 audit_logs 기록
- [ ] Runbook-015 (Auth): 세부 점검 항목 #15 수행 및 audit_logs 기록
- [ ] Runbook-016 (Auth): 세부 점검 항목 #16 수행 및 audit_logs 기록
- [ ] Runbook-017 (Auth): 세부 점검 항목 #17 수행 및 audit_logs 기록
- [ ] Runbook-018 (Auth): 세부 점검 항목 #18 수행 및 audit_logs 기록
- [ ] Runbook-019 (Auth): 세부 점검 항목 #19 수행 및 audit_logs 기록
- [ ] Runbook-020 (Auth): 세부 점검 항목 #20 수행 및 audit_logs 기록
- [ ] Runbook-021 (Auth): 세부 점검 항목 #21 수행 및 audit_logs 기록
- [ ] Runbook-022 (Auth): 세부 점검 항목 #22 수행 및 audit_logs 기록
- [ ] Runbook-023 (Auth): 세부 점검 항목 #23 수행 및 audit_logs 기록
- [ ] Runbook-024 (Auth): 세부 점검 항목 #24 수행 및 audit_logs 기록
- [ ] Runbook-025 (Auth): 세부 점검 항목 #25 수행 및 audit_logs 기록
- [ ] Runbook-026 (Auth): 세부 점검 항목 #26 수행 및 audit_logs 기록
- [ ] Runbook-027 (Auth): 세부 점검 항목 #27 수행 및 audit_logs 기록
- [ ] Runbook-028 (Auth): 세부 점검 항목 #28 수행 및 audit_logs 기록
- [ ] Runbook-029 (Auth): 세부 점검 항목 #29 수행 및 audit_logs 기록
- [ ] Runbook-030 (Auth): 세부 점검 항목 #30 수행 및 audit_logs 기록
- [ ] Runbook-031 (Auth): 세부 점검 항목 #31 수행 및 audit_logs 기록
- [ ] Runbook-032 (Auth): 세부 점검 항목 #32 수행 및 audit_logs 기록
- [ ] Runbook-033 (Auth): 세부 점검 항목 #33 수행 및 audit_logs 기록
- [ ] Runbook-034 (Auth): 세부 점검 항목 #34 수행 및 audit_logs 기록
- [ ] Runbook-035 (Auth): 세부 점검 항목 #35 수행 및 audit_logs 기록
- [ ] Runbook-036 (Auth): 세부 점검 항목 #36 수행 및 audit_logs 기록
- [ ] Runbook-037 (Auth): 세부 점검 항목 #37 수행 및 audit_logs 기록
- [ ] Runbook-038 (Auth): 세부 점검 항목 #38 수행 및 audit_logs 기록
- [ ] Runbook-039 (Auth): 세부 점검 항목 #39 수행 및 audit_logs 기록
- [ ] Runbook-040 (Auth): 세부 점검 항목 #40 수행 및 audit_logs 기록
- [ ] Runbook-041 (Auth): 세부 점검 항목 #41 수행 및 audit_logs 기록
- [ ] Runbook-042 (Auth): 세부 점검 항목 #42 수행 및 audit_logs 기록
- [ ] Runbook-043 (Auth): 세부 점검 항목 #43 수행 및 audit_logs 기록
- [ ] Runbook-044 (Auth): 세부 점검 항목 #44 수행 및 audit_logs 기록
- [ ] Runbook-045 (Auth): 세부 점검 항목 #45 수행 및 audit_logs 기록
- [ ] Runbook-046 (Auth): 세부 점검 항목 #46 수행 및 audit_logs 기록
- [ ] Runbook-047 (Auth): 세부 점검 항목 #47 수행 및 audit_logs 기록
- [ ] Runbook-048 (Auth): 세부 점검 항목 #48 수행 및 audit_logs 기록
- [ ] Runbook-049 (Auth): 세부 점검 항목 #49 수행 및 audit_logs 기록
- [ ] Runbook-050 (Auth): 세부 점검 항목 #50 수행 및 audit_logs 기록
- [ ] Runbook-051 (Auth): 세부 점검 항목 #51 수행 및 audit_logs 기록
- [ ] Runbook-052 (Auth): 세부 점검 항목 #52 수행 및 audit_logs 기록
- [ ] Runbook-053 (Auth): 세부 점검 항목 #53 수행 및 audit_logs 기록
- [ ] Runbook-054 (Auth): 세부 점검 항목 #54 수행 및 audit_logs 기록
- [ ] Runbook-055 (Auth): 세부 점검 항목 #55 수행 및 audit_logs 기록
- [ ] Runbook-056 (Auth): 세부 점검 항목 #56 수행 및 audit_logs 기록
- [ ] Runbook-057 (Auth): 세부 점검 항목 #57 수행 및 audit_logs 기록
- [ ] Runbook-058 (Auth): 세부 점검 항목 #58 수행 및 audit_logs 기록
- [ ] Runbook-059 (Auth): 세부 점검 항목 #59 수행 및 audit_logs 기록
- [ ] Runbook-060 (Auth): 세부 점검 항목 #60 수행 및 audit_logs 기록
- [ ] Runbook-061 (Auth): 세부 점검 항목 #61 수행 및 audit_logs 기록
- [ ] Runbook-062 (Auth): 세부 점검 항목 #62 수행 및 audit_logs 기록
- [ ] Runbook-063 (Auth): 세부 점검 항목 #63 수행 및 audit_logs 기록
- [ ] Runbook-064 (Auth): 세부 점검 항목 #64 수행 및 audit_logs 기록
- [ ] Runbook-065 (Auth): 세부 점검 항목 #65 수행 및 audit_logs 기록
- [ ] Runbook-066 (Auth): 세부 점검 항목 #66 수행 및 audit_logs 기록
- [ ] Runbook-067 (Auth): 세부 점검 항목 #67 수행 및 audit_logs 기록
- [ ] Runbook-068 (Auth): 세부 점검 항목 #68 수행 및 audit_logs 기록
- [ ] Runbook-069 (Auth): 세부 점검 항목 #69 수행 및 audit_logs 기록
- [ ] Runbook-070 (Auth): 세부 점검 항목 #70 수행 및 audit_logs 기록
- [ ] Runbook-071 (Auth): 세부 점검 항목 #71 수행 및 audit_logs 기록
- [ ] Runbook-072 (Auth): 세부 점검 항목 #72 수행 및 audit_logs 기록
- [ ] Runbook-073 (Auth): 세부 점검 항목 #73 수행 및 audit_logs 기록
- [ ] Runbook-074 (Auth): 세부 점검 항목 #74 수행 및 audit_logs 기록
- [ ] Runbook-075 (Auth): 세부 점검 항목 #75 수행 및 audit_logs 기록
- [ ] Runbook-076 (Auth): 세부 점검 항목 #76 수행 및 audit_logs 기록
- [ ] Runbook-077 (Auth): 세부 점검 항목 #77 수행 및 audit_logs 기록
- [ ] Runbook-078 (Auth): 세부 점검 항목 #78 수행 및 audit_logs 기록
- [ ] Runbook-079 (Auth): 세부 점검 항목 #79 수행 및 audit_logs 기록
- [ ] Runbook-080 (Auth): 세부 점검 항목 #80 수행 및 audit_logs 기록
- [ ] Runbook-081 (Data): 세부 점검 항목 #81 수행 및 audit_logs 기록
- [ ] Runbook-082 (Data): 세부 점검 항목 #82 수행 및 audit_logs 기록
- [ ] Runbook-083 (Data): 세부 점검 항목 #83 수행 및 audit_logs 기록
- [ ] Runbook-084 (Data): 세부 점검 항목 #84 수행 및 audit_logs 기록
- [ ] Runbook-085 (Data): 세부 점검 항목 #85 수행 및 audit_logs 기록
- [ ] Runbook-086 (Data): 세부 점검 항목 #86 수행 및 audit_logs 기록
- [ ] Runbook-087 (Data): 세부 점검 항목 #87 수행 및 audit_logs 기록
- [ ] Runbook-088 (Data): 세부 점검 항목 #88 수행 및 audit_logs 기록
- [ ] Runbook-089 (Data): 세부 점검 항목 #89 수행 및 audit_logs 기록
- [ ] Runbook-090 (Data): 세부 점검 항목 #90 수행 및 audit_logs 기록
- [ ] Runbook-091 (Data): 세부 점검 항목 #91 수행 및 audit_logs 기록
- [ ] Runbook-092 (Data): 세부 점검 항목 #92 수행 및 audit_logs 기록
- [ ] Runbook-093 (Data): 세부 점검 항목 #93 수행 및 audit_logs 기록
- [ ] Runbook-094 (Data): 세부 점검 항목 #94 수행 및 audit_logs 기록
- [ ] Runbook-095 (Data): 세부 점검 항목 #95 수행 및 audit_logs 기록
- [ ] Runbook-096 (Data): 세부 점검 항목 #96 수행 및 audit_logs 기록
- [ ] Runbook-097 (Data): 세부 점검 항목 #97 수행 및 audit_logs 기록
- [ ] Runbook-098 (Data): 세부 점검 항목 #98 수행 및 audit_logs 기록
- [ ] Runbook-099 (Data): 세부 점검 항목 #99 수행 및 audit_logs 기록
- [ ] Runbook-100 (Data): 세부 점검 항목 #100 수행 및 audit_logs 기록
- [ ] Runbook-101 (Data): 세부 점검 항목 #101 수행 및 audit_logs 기록
- [ ] Runbook-102 (Data): 세부 점검 항목 #102 수행 및 audit_logs 기록
- [ ] Runbook-103 (Data): 세부 점검 항목 #103 수행 및 audit_logs 기록
- [ ] Runbook-104 (Data): 세부 점검 항목 #104 수행 및 audit_logs 기록
- [ ] Runbook-105 (Data): 세부 점검 항목 #105 수행 및 audit_logs 기록
- [ ] Runbook-106 (Data): 세부 점검 항목 #106 수행 및 audit_logs 기록
- [ ] Runbook-107 (Data): 세부 점검 항목 #107 수행 및 audit_logs 기록
- [ ] Runbook-108 (Data): 세부 점검 항목 #108 수행 및 audit_logs 기록
- [ ] Runbook-109 (Data): 세부 점검 항목 #109 수행 및 audit_logs 기록
- [ ] Runbook-110 (Data): 세부 점검 항목 #110 수행 및 audit_logs 기록
- [ ] Runbook-111 (Data): 세부 점검 항목 #111 수행 및 audit_logs 기록
- [ ] Runbook-112 (Data): 세부 점검 항목 #112 수행 및 audit_logs 기록
- [ ] Runbook-113 (Data): 세부 점검 항목 #113 수행 및 audit_logs 기록
- [ ] Runbook-114 (Data): 세부 점검 항목 #114 수행 및 audit_logs 기록
- [ ] Runbook-115 (Data): 세부 점검 항목 #115 수행 및 audit_logs 기록
- [ ] Runbook-116 (Data): 세부 점검 항목 #116 수행 및 audit_logs 기록
- [ ] Runbook-117 (Data): 세부 점검 항목 #117 수행 및 audit_logs 기록
- [ ] Runbook-118 (Data): 세부 점검 항목 #118 수행 및 audit_logs 기록
- [ ] Runbook-119 (Data): 세부 점검 항목 #119 수행 및 audit_logs 기록
- [ ] Runbook-120 (Data): 세부 점검 항목 #120 수행 및 audit_logs 기록
- [ ] Runbook-121 (Data): 세부 점검 항목 #121 수행 및 audit_logs 기록
- [ ] Runbook-122 (Data): 세부 점검 항목 #122 수행 및 audit_logs 기록
- [ ] Runbook-123 (Data): 세부 점검 항목 #123 수행 및 audit_logs 기록
- [ ] Runbook-124 (Data): 세부 점검 항목 #124 수행 및 audit_logs 기록
- [ ] Runbook-125 (Data): 세부 점검 항목 #125 수행 및 audit_logs 기록
- [ ] Runbook-126 (Data): 세부 점검 항목 #126 수행 및 audit_logs 기록
- [ ] Runbook-127 (Data): 세부 점검 항목 #127 수행 및 audit_logs 기록
- [ ] Runbook-128 (Data): 세부 점검 항목 #128 수행 및 audit_logs 기록
- [ ] Runbook-129 (Data): 세부 점검 항목 #129 수행 및 audit_logs 기록
- [ ] Runbook-130 (Data): 세부 점검 항목 #130 수행 및 audit_logs 기록
- [ ] Runbook-131 (Data): 세부 점검 항목 #131 수행 및 audit_logs 기록
- [ ] Runbook-132 (Data): 세부 점검 항목 #132 수행 및 audit_logs 기록
- [ ] Runbook-133 (Data): 세부 점검 항목 #133 수행 및 audit_logs 기록
- [ ] Runbook-134 (Data): 세부 점검 항목 #134 수행 및 audit_logs 기록
- [ ] Runbook-135 (Data): 세부 점검 항목 #135 수행 및 audit_logs 기록
- [ ] Runbook-136 (Data): 세부 점검 항목 #136 수행 및 audit_logs 기록
- [ ] Runbook-137 (Data): 세부 점검 항목 #137 수행 및 audit_logs 기록
- [ ] Runbook-138 (Data): 세부 점검 항목 #138 수행 및 audit_logs 기록
- [ ] Runbook-139 (Data): 세부 점검 항목 #139 수행 및 audit_logs 기록
- [ ] Runbook-140 (Data): 세부 점검 항목 #140 수행 및 audit_logs 기록
- [ ] Runbook-141 (Data): 세부 점검 항목 #141 수행 및 audit_logs 기록
- [ ] Runbook-142 (Data): 세부 점검 항목 #142 수행 및 audit_logs 기록
- [ ] Runbook-143 (Data): 세부 점검 항목 #143 수행 및 audit_logs 기록
- [ ] Runbook-144 (Data): 세부 점검 항목 #144 수행 및 audit_logs 기록
- [ ] Runbook-145 (Data): 세부 점검 항목 #145 수행 및 audit_logs 기록
- [ ] Runbook-146 (Data): 세부 점검 항목 #146 수행 및 audit_logs 기록
- [ ] Runbook-147 (Data): 세부 점검 항목 #147 수행 및 audit_logs 기록
- [ ] Runbook-148 (Data): 세부 점검 항목 #148 수행 및 audit_logs 기록
- [ ] Runbook-149 (Data): 세부 점검 항목 #149 수행 및 audit_logs 기록
- [ ] Runbook-150 (Data): 세부 점검 항목 #150 수행 및 audit_logs 기록
- [ ] Runbook-151 (Data): 세부 점검 항목 #151 수행 및 audit_logs 기록
- [ ] Runbook-152 (Data): 세부 점검 항목 #152 수행 및 audit_logs 기록
- [ ] Runbook-153 (Data): 세부 점검 항목 #153 수행 및 audit_logs 기록
- [ ] Runbook-154 (Data): 세부 점검 항목 #154 수행 및 audit_logs 기록
- [ ] Runbook-155 (Data): 세부 점검 항목 #155 수행 및 audit_logs 기록
- [ ] Runbook-156 (Data): 세부 점검 항목 #156 수행 및 audit_logs 기록
- [ ] Runbook-157 (Data): 세부 점검 항목 #157 수행 및 audit_logs 기록
- [ ] Runbook-158 (Data): 세부 점검 항목 #158 수행 및 audit_logs 기록
- [ ] Runbook-159 (Data): 세부 점검 항목 #159 수행 및 audit_logs 기록
- [ ] Runbook-160 (Data): 세부 점검 항목 #160 수행 및 audit_logs 기록
- [ ] Runbook-161 (Data): 세부 점검 항목 #161 수행 및 audit_logs 기록
- [ ] Runbook-162 (Data): 세부 점검 항목 #162 수행 및 audit_logs 기록
- [ ] Runbook-163 (Data): 세부 점검 항목 #163 수행 및 audit_logs 기록
- [ ] Runbook-164 (Data): 세부 점검 항목 #164 수행 및 audit_logs 기록
- [ ] Runbook-165 (Data): 세부 점검 항목 #165 수행 및 audit_logs 기록
- [ ] Runbook-166 (Data): 세부 점검 항목 #166 수행 및 audit_logs 기록
- [ ] Runbook-167 (Data): 세부 점검 항목 #167 수행 및 audit_logs 기록
- [ ] Runbook-168 (Data): 세부 점검 항목 #168 수행 및 audit_logs 기록
- [ ] Runbook-169 (Data): 세부 점검 항목 #169 수행 및 audit_logs 기록
- [ ] Runbook-170 (Data): 세부 점검 항목 #170 수행 및 audit_logs 기록
- [ ] Runbook-171 (Ops): 세부 점검 항목 #171 수행 및 audit_logs 기록
- [ ] Runbook-172 (Ops): 세부 점검 항목 #172 수행 및 audit_logs 기록
- [ ] Runbook-173 (Ops): 세부 점검 항목 #173 수행 및 audit_logs 기록
- [ ] Runbook-174 (Ops): 세부 점검 항목 #174 수행 및 audit_logs 기록
- [ ] Runbook-175 (Ops): 세부 점검 항목 #175 수행 및 audit_logs 기록
- [ ] Runbook-176 (Ops): 세부 점검 항목 #176 수행 및 audit_logs 기록
- [ ] Runbook-177 (Ops): 세부 점검 항목 #177 수행 및 audit_logs 기록
- [ ] Runbook-178 (Ops): 세부 점검 항목 #178 수행 및 audit_logs 기록
- [ ] Runbook-179 (Ops): 세부 점검 항목 #179 수행 및 audit_logs 기록
- [ ] Runbook-180 (Ops): 세부 점검 항목 #180 수행 및 audit_logs 기록
- [ ] Runbook-181 (Ops): 세부 점검 항목 #181 수행 및 audit_logs 기록
- [ ] Runbook-182 (Ops): 세부 점검 항목 #182 수행 및 audit_logs 기록
- [ ] Runbook-183 (Ops): 세부 점검 항목 #183 수행 및 audit_logs 기록
- [ ] Runbook-184 (Ops): 세부 점검 항목 #184 수행 및 audit_logs 기록
- [ ] Runbook-185 (Ops): 세부 점검 항목 #185 수행 및 audit_logs 기록
- [ ] Runbook-186 (Ops): 세부 점검 항목 #186 수행 및 audit_logs 기록
- [ ] Runbook-187 (Ops): 세부 점검 항목 #187 수행 및 audit_logs 기록
- [ ] Runbook-188 (Ops): 세부 점검 항목 #188 수행 및 audit_logs 기록
- [ ] Runbook-189 (Ops): 세부 점검 항목 #189 수행 및 audit_logs 기록
- [ ] Runbook-190 (Ops): 세부 점검 항목 #190 수행 및 audit_logs 기록
- [ ] Runbook-191 (Ops): 세부 점검 항목 #191 수행 및 audit_logs 기록
- [ ] Runbook-192 (Ops): 세부 점검 항목 #192 수행 및 audit_logs 기록
- [ ] Runbook-193 (Ops): 세부 점검 항목 #193 수행 및 audit_logs 기록
- [ ] Runbook-194 (Ops): 세부 점검 항목 #194 수행 및 audit_logs 기록
- [ ] Runbook-195 (Ops): 세부 점검 항목 #195 수행 및 audit_logs 기록
- [ ] Runbook-196 (Ops): 세부 점검 항목 #196 수행 및 audit_logs 기록
- [ ] Runbook-197 (Ops): 세부 점검 항목 #197 수행 및 audit_logs 기록
- [ ] Runbook-198 (Ops): 세부 점검 항목 #198 수행 및 audit_logs 기록
- [ ] Runbook-199 (Ops): 세부 점검 항목 #199 수행 및 audit_logs 기록
- [ ] Runbook-200 (Ops): 세부 점검 항목 #200 수행 및 audit_logs 기록
- [ ] Runbook-201 (Ops): 세부 점검 항목 #201 수행 및 audit_logs 기록
- [ ] Runbook-202 (Ops): 세부 점검 항목 #202 수행 및 audit_logs 기록
- [ ] Runbook-203 (Ops): 세부 점검 항목 #203 수행 및 audit_logs 기록
- [ ] Runbook-204 (Ops): 세부 점검 항목 #204 수행 및 audit_logs 기록
- [ ] Runbook-205 (Ops): 세부 점검 항목 #205 수행 및 audit_logs 기록
- [ ] Runbook-206 (Ops): 세부 점검 항목 #206 수행 및 audit_logs 기록
- [ ] Runbook-207 (Ops): 세부 점검 항목 #207 수행 및 audit_logs 기록
- [ ] Runbook-208 (Ops): 세부 점검 항목 #208 수행 및 audit_logs 기록
- [ ] Runbook-209 (Ops): 세부 점검 항목 #209 수행 및 audit_logs 기록
- [ ] Runbook-210 (Ops): 세부 점검 항목 #210 수행 및 audit_logs 기록
- [ ] Runbook-211 (Ops): 세부 점검 항목 #211 수행 및 audit_logs 기록
- [ ] Runbook-212 (Ops): 세부 점검 항목 #212 수행 및 audit_logs 기록
- [ ] Runbook-213 (Ops): 세부 점검 항목 #213 수행 및 audit_logs 기록
- [ ] Runbook-214 (Ops): 세부 점검 항목 #214 수행 및 audit_logs 기록
- [ ] Runbook-215 (Ops): 세부 점검 항목 #215 수행 및 audit_logs 기록
- [ ] Runbook-216 (Ops): 세부 점검 항목 #216 수행 및 audit_logs 기록
- [ ] Runbook-217 (Ops): 세부 점검 항목 #217 수행 및 audit_logs 기록
- [ ] Runbook-218 (Ops): 세부 점검 항목 #218 수행 및 audit_logs 기록
- [ ] Runbook-219 (Ops): 세부 점검 항목 #219 수행 및 audit_logs 기록
- [ ] Runbook-220 (Ops): 세부 점검 항목 #220 수행 및 audit_logs 기록
- [ ] Runbook-221 (Ops): 세부 점검 항목 #221 수행 및 audit_logs 기록
- [ ] Runbook-222 (Ops): 세부 점검 항목 #222 수행 및 audit_logs 기록
- [ ] Runbook-223 (Ops): 세부 점검 항목 #223 수행 및 audit_logs 기록
- [ ] Runbook-224 (Ops): 세부 점검 항목 #224 수행 및 audit_logs 기록
- [ ] Runbook-225 (Ops): 세부 점검 항목 #225 수행 및 audit_logs 기록
- [ ] Runbook-226 (Ops): 세부 점검 항목 #226 수행 및 audit_logs 기록
- [ ] Runbook-227 (Ops): 세부 점검 항목 #227 수행 및 audit_logs 기록
- [ ] Runbook-228 (Ops): 세부 점검 항목 #228 수행 및 audit_logs 기록
- [ ] Runbook-229 (Ops): 세부 점검 항목 #229 수행 및 audit_logs 기록
- [ ] Runbook-230 (Ops): 세부 점검 항목 #230 수행 및 audit_logs 기록
- [ ] Runbook-231 (Ops): 세부 점검 항목 #231 수행 및 audit_logs 기록
- [ ] Runbook-232 (Ops): 세부 점검 항목 #232 수행 및 audit_logs 기록
- [ ] Runbook-233 (Ops): 세부 점검 항목 #233 수행 및 audit_logs 기록
- [ ] Runbook-234 (Ops): 세부 점검 항목 #234 수행 및 audit_logs 기록
- [ ] Runbook-235 (Ops): 세부 점검 항목 #235 수행 및 audit_logs 기록
- [ ] Runbook-236 (Ops): 세부 점검 항목 #236 수행 및 audit_logs 기록
- [ ] Runbook-237 (Ops): 세부 점검 항목 #237 수행 및 audit_logs 기록
- [ ] Runbook-238 (Ops): 세부 점검 항목 #238 수행 및 audit_logs 기록
- [ ] Runbook-239 (Ops): 세부 점검 항목 #239 수행 및 audit_logs 기록
- [ ] Runbook-240 (Ops): 세부 점검 항목 #240 수행 및 audit_logs 기록
- [ ] Runbook-241 (Ops): 세부 점검 항목 #241 수행 및 audit_logs 기록
- [ ] Runbook-242 (Ops): 세부 점검 항목 #242 수행 및 audit_logs 기록
- [ ] Runbook-243 (Ops): 세부 점검 항목 #243 수행 및 audit_logs 기록
- [ ] Runbook-244 (Ops): 세부 점검 항목 #244 수행 및 audit_logs 기록
- [ ] Runbook-245 (Ops): 세부 점검 항목 #245 수행 및 audit_logs 기록
- [ ] Runbook-246 (Ops): 세부 점검 항목 #246 수행 및 audit_logs 기록
- [ ] Runbook-247 (Ops): 세부 점검 항목 #247 수행 및 audit_logs 기록
- [ ] Runbook-248 (Ops): 세부 점검 항목 #248 수행 및 audit_logs 기록
- [ ] Runbook-249 (Ops): 세부 점검 항목 #249 수행 및 audit_logs 기록
- [ ] Runbook-250 (Ops): 세부 점검 항목 #250 수행 및 audit_logs 기록
- [ ] Runbook-251 (Scale): 세부 점검 항목 #251 수행 및 audit_logs 기록
- [ ] Runbook-252 (Scale): 세부 점검 항목 #252 수행 및 audit_logs 기록
- [ ] Runbook-253 (Scale): 세부 점검 항목 #253 수행 및 audit_logs 기록
- [ ] Runbook-254 (Scale): 세부 점검 항목 #254 수행 및 audit_logs 기록
- [ ] Runbook-255 (Scale): 세부 점검 항목 #255 수행 및 audit_logs 기록
- [ ] Runbook-256 (Scale): 세부 점검 항목 #256 수행 및 audit_logs 기록
- [ ] Runbook-257 (Scale): 세부 점검 항목 #257 수행 및 audit_logs 기록
- [ ] Runbook-258 (Scale): 세부 점검 항목 #258 수행 및 audit_logs 기록
- [ ] Runbook-259 (Scale): 세부 점검 항목 #259 수행 및 audit_logs 기록
- [ ] Runbook-260 (Scale): 세부 점검 항목 #260 수행 및 audit_logs 기록
- [ ] Runbook-261 (Scale): 세부 점검 항목 #261 수행 및 audit_logs 기록
- [ ] Runbook-262 (Scale): 세부 점검 항목 #262 수행 및 audit_logs 기록
- [ ] Runbook-263 (Scale): 세부 점검 항목 #263 수행 및 audit_logs 기록
- [ ] Runbook-264 (Scale): 세부 점검 항목 #264 수행 및 audit_logs 기록
- [ ] Runbook-265 (Scale): 세부 점검 항목 #265 수행 및 audit_logs 기록
- [ ] Runbook-266 (Scale): 세부 점검 항목 #266 수행 및 audit_logs 기록
- [ ] Runbook-267 (Scale): 세부 점검 항목 #267 수행 및 audit_logs 기록
- [ ] Runbook-268 (Scale): 세부 점검 항목 #268 수행 및 audit_logs 기록
- [ ] Runbook-269 (Scale): 세부 점검 항목 #269 수행 및 audit_logs 기록
- [ ] Runbook-270 (Scale): 세부 점검 항목 #270 수행 및 audit_logs 기록
- [ ] Runbook-271 (Scale): 세부 점검 항목 #271 수행 및 audit_logs 기록
- [ ] Runbook-272 (Scale): 세부 점검 항목 #272 수행 및 audit_logs 기록
- [ ] Runbook-273 (Scale): 세부 점검 항목 #273 수행 및 audit_logs 기록
- [ ] Runbook-274 (Scale): 세부 점검 항목 #274 수행 및 audit_logs 기록
- [ ] Runbook-275 (Scale): 세부 점검 항목 #275 수행 및 audit_logs 기록
- [ ] Runbook-276 (Scale): 세부 점검 항목 #276 수행 및 audit_logs 기록
- [ ] Runbook-277 (Scale): 세부 점검 항목 #277 수행 및 audit_logs 기록
- [ ] Runbook-278 (Scale): 세부 점검 항목 #278 수행 및 audit_logs 기록
- [ ] Runbook-279 (Scale): 세부 점검 항목 #279 수행 및 audit_logs 기록
- [ ] Runbook-280 (Scale): 세부 점검 항목 #280 수행 및 audit_logs 기록
- [ ] Runbook-281 (Scale): 세부 점검 항목 #281 수행 및 audit_logs 기록
- [ ] Runbook-282 (Scale): 세부 점검 항목 #282 수행 및 audit_logs 기록
- [ ] Runbook-283 (Scale): 세부 점검 항목 #283 수행 및 audit_logs 기록
- [ ] Runbook-284 (Scale): 세부 점검 항목 #284 수행 및 audit_logs 기록
- [ ] Runbook-285 (Scale): 세부 점검 항목 #285 수행 및 audit_logs 기록
- [ ] Runbook-286 (Scale): 세부 점검 항목 #286 수행 및 audit_logs 기록
- [ ] Runbook-287 (Scale): 세부 점검 항목 #287 수행 및 audit_logs 기록
- [ ] Runbook-288 (Scale): 세부 점검 항목 #288 수행 및 audit_logs 기록
- [ ] Runbook-289 (Scale): 세부 점검 항목 #289 수행 및 audit_logs 기록
- [ ] Runbook-290 (Scale): 세부 점검 항목 #290 수행 및 audit_logs 기록
- [ ] Runbook-291 (Scale): 세부 점검 항목 #291 수행 및 audit_logs 기록
- [ ] Runbook-292 (Scale): 세부 점검 항목 #292 수행 및 audit_logs 기록
- [ ] Runbook-293 (Scale): 세부 점검 항목 #293 수행 및 audit_logs 기록
- [ ] Runbook-294 (Scale): 세부 점검 항목 #294 수행 및 audit_logs 기록
- [ ] Runbook-295 (Scale): 세부 점검 항목 #295 수행 및 audit_logs 기록
- [ ] Runbook-296 (Scale): 세부 점검 항목 #296 수행 및 audit_logs 기록
- [ ] Runbook-297 (Scale): 세부 점검 항목 #297 수행 및 audit_logs 기록
- [ ] Runbook-298 (Scale): 세부 점검 항목 #298 수행 및 audit_logs 기록
- [ ] Runbook-299 (Scale): 세부 점검 항목 #299 수행 및 audit_logs 기록
- [ ] Runbook-300 (Scale): 세부 점검 항목 #300 수행 및 audit_logs 기록
- [ ] Runbook-301 (Scale): 세부 점검 항목 #301 수행 및 audit_logs 기록
- [ ] Runbook-302 (Scale): 세부 점검 항목 #302 수행 및 audit_logs 기록
- [ ] Runbook-303 (Scale): 세부 점검 항목 #303 수행 및 audit_logs 기록
- [ ] Runbook-304 (Scale): 세부 점검 항목 #304 수행 및 audit_logs 기록
- [ ] Runbook-305 (Scale): 세부 점검 항목 #305 수행 및 audit_logs 기록
- [ ] Runbook-306 (Scale): 세부 점검 항목 #306 수행 및 audit_logs 기록
- [ ] Runbook-307 (Scale): 세부 점검 항목 #307 수행 및 audit_logs 기록
- [ ] Runbook-308 (Scale): 세부 점검 항목 #308 수행 및 audit_logs 기록
- [ ] Runbook-309 (Scale): 세부 점검 항목 #309 수행 및 audit_logs 기록
- [ ] Runbook-310 (Scale): 세부 점검 항목 #310 수행 및 audit_logs 기록
- [ ] Runbook-311 (Scale): 세부 점검 항목 #311 수행 및 audit_logs 기록
- [ ] Runbook-312 (Scale): 세부 점검 항목 #312 수행 및 audit_logs 기록
- [ ] Runbook-313 (Scale): 세부 점검 항목 #313 수행 및 audit_logs 기록
- [ ] Runbook-314 (Scale): 세부 점검 항목 #314 수행 및 audit_logs 기록
- [ ] Runbook-315 (Scale): 세부 점검 항목 #315 수행 및 audit_logs 기록
- [ ] Runbook-316 (Scale): 세부 점검 항목 #316 수행 및 audit_logs 기록
- [ ] Runbook-317 (Scale): 세부 점검 항목 #317 수행 및 audit_logs 기록
- [ ] Runbook-318 (Scale): 세부 점검 항목 #318 수행 및 audit_logs 기록
- [ ] Runbook-319 (Scale): 세부 점검 항목 #319 수행 및 audit_logs 기록
- [ ] Runbook-320 (Scale): 세부 점검 항목 #320 수행 및 audit_logs 기록

## 19. 부록 C. 테스트 시나리오 (E2E + 보안 + 성능)

- TC-001 [E2E] 입력/예상결과/로그검증 포함
- TC-002 [E2E] 입력/예상결과/로그검증 포함
- TC-003 [E2E] 입력/예상결과/로그검증 포함
- TC-004 [E2E] 입력/예상결과/로그검증 포함
- TC-005 [E2E] 입력/예상결과/로그검증 포함
- TC-006 [E2E] 입력/예상결과/로그검증 포함
- TC-007 [E2E] 입력/예상결과/로그검증 포함
- TC-008 [E2E] 입력/예상결과/로그검증 포함
- TC-009 [E2E] 입력/예상결과/로그검증 포함
- TC-010 [E2E] 입력/예상결과/로그검증 포함
- TC-011 [E2E] 입력/예상결과/로그검증 포함
- TC-012 [E2E] 입력/예상결과/로그검증 포함
- TC-013 [E2E] 입력/예상결과/로그검증 포함
- TC-014 [E2E] 입력/예상결과/로그검증 포함
- TC-015 [E2E] 입력/예상결과/로그검증 포함
- TC-016 [E2E] 입력/예상결과/로그검증 포함
- TC-017 [E2E] 입력/예상결과/로그검증 포함
- TC-018 [E2E] 입력/예상결과/로그검증 포함
- TC-019 [E2E] 입력/예상결과/로그검증 포함
- TC-020 [E2E] 입력/예상결과/로그검증 포함
- TC-021 [E2E] 입력/예상결과/로그검증 포함
- TC-022 [E2E] 입력/예상결과/로그검증 포함
- TC-023 [E2E] 입력/예상결과/로그검증 포함
- TC-024 [E2E] 입력/예상결과/로그검증 포함
- TC-025 [E2E] 입력/예상결과/로그검증 포함
- TC-026 [E2E] 입력/예상결과/로그검증 포함
- TC-027 [E2E] 입력/예상결과/로그검증 포함
- TC-028 [E2E] 입력/예상결과/로그검증 포함
- TC-029 [E2E] 입력/예상결과/로그검증 포함
- TC-030 [E2E] 입력/예상결과/로그검증 포함
- TC-031 [E2E] 입력/예상결과/로그검증 포함
- TC-032 [E2E] 입력/예상결과/로그검증 포함
- TC-033 [E2E] 입력/예상결과/로그검증 포함
- TC-034 [E2E] 입력/예상결과/로그검증 포함
- TC-035 [E2E] 입력/예상결과/로그검증 포함
- TC-036 [E2E] 입력/예상결과/로그검증 포함
- TC-037 [E2E] 입력/예상결과/로그검증 포함
- TC-038 [E2E] 입력/예상결과/로그검증 포함
- TC-039 [E2E] 입력/예상결과/로그검증 포함
- TC-040 [E2E] 입력/예상결과/로그검증 포함
- TC-041 [E2E] 입력/예상결과/로그검증 포함
- TC-042 [E2E] 입력/예상결과/로그검증 포함
- TC-043 [E2E] 입력/예상결과/로그검증 포함
- TC-044 [E2E] 입력/예상결과/로그검증 포함
- TC-045 [E2E] 입력/예상결과/로그검증 포함
- TC-046 [E2E] 입력/예상결과/로그검증 포함
- TC-047 [E2E] 입력/예상결과/로그검증 포함
- TC-048 [E2E] 입력/예상결과/로그검증 포함
- TC-049 [E2E] 입력/예상결과/로그검증 포함
- TC-050 [E2E] 입력/예상결과/로그검증 포함
- TC-051 [E2E] 입력/예상결과/로그검증 포함
- TC-052 [E2E] 입력/예상결과/로그검증 포함
- TC-053 [E2E] 입력/예상결과/로그검증 포함
- TC-054 [E2E] 입력/예상결과/로그검증 포함
- TC-055 [E2E] 입력/예상결과/로그검증 포함
- TC-056 [E2E] 입력/예상결과/로그검증 포함
- TC-057 [E2E] 입력/예상결과/로그검증 포함
- TC-058 [E2E] 입력/예상결과/로그검증 포함
- TC-059 [E2E] 입력/예상결과/로그검증 포함
- TC-060 [E2E] 입력/예상결과/로그검증 포함
- TC-061 [E2E] 입력/예상결과/로그검증 포함
- TC-062 [E2E] 입력/예상결과/로그검증 포함
- TC-063 [E2E] 입력/예상결과/로그검증 포함
- TC-064 [E2E] 입력/예상결과/로그검증 포함
- TC-065 [E2E] 입력/예상결과/로그검증 포함
- TC-066 [E2E] 입력/예상결과/로그검증 포함
- TC-067 [E2E] 입력/예상결과/로그검증 포함
- TC-068 [E2E] 입력/예상결과/로그검증 포함
- TC-069 [E2E] 입력/예상결과/로그검증 포함
- TC-070 [E2E] 입력/예상결과/로그검증 포함
- TC-071 [E2E] 입력/예상결과/로그검증 포함
- TC-072 [E2E] 입력/예상결과/로그검증 포함
- TC-073 [E2E] 입력/예상결과/로그검증 포함
- TC-074 [E2E] 입력/예상결과/로그검증 포함
- TC-075 [E2E] 입력/예상결과/로그검증 포함
- TC-076 [E2E] 입력/예상결과/로그검증 포함
- TC-077 [E2E] 입력/예상결과/로그검증 포함
- TC-078 [E2E] 입력/예상결과/로그검증 포함
- TC-079 [E2E] 입력/예상결과/로그검증 포함
- TC-080 [E2E] 입력/예상결과/로그검증 포함
- TC-081 [E2E] 입력/예상결과/로그검증 포함
- TC-082 [E2E] 입력/예상결과/로그검증 포함
- TC-083 [E2E] 입력/예상결과/로그검증 포함
- TC-084 [E2E] 입력/예상결과/로그검증 포함
- TC-085 [E2E] 입력/예상결과/로그검증 포함
- TC-086 [E2E] 입력/예상결과/로그검증 포함
- TC-087 [E2E] 입력/예상결과/로그검증 포함
- TC-088 [E2E] 입력/예상결과/로그검증 포함
- TC-089 [E2E] 입력/예상결과/로그검증 포함
- TC-090 [E2E] 입력/예상결과/로그검증 포함
- TC-091 [E2E] 입력/예상결과/로그검증 포함
- TC-092 [E2E] 입력/예상결과/로그검증 포함
- TC-093 [E2E] 입력/예상결과/로그검증 포함
- TC-094 [E2E] 입력/예상결과/로그검증 포함
- TC-095 [E2E] 입력/예상결과/로그검증 포함
- TC-096 [E2E] 입력/예상결과/로그검증 포함
- TC-097 [E2E] 입력/예상결과/로그검증 포함
- TC-098 [E2E] 입력/예상결과/로그검증 포함
- TC-099 [E2E] 입력/예상결과/로그검증 포함
- TC-100 [E2E] 입력/예상결과/로그검증 포함
- TC-101 [E2E] 입력/예상결과/로그검증 포함
- TC-102 [E2E] 입력/예상결과/로그검증 포함
- TC-103 [E2E] 입력/예상결과/로그검증 포함
- TC-104 [E2E] 입력/예상결과/로그검증 포함
- TC-105 [E2E] 입력/예상결과/로그검증 포함
- TC-106 [E2E] 입력/예상결과/로그검증 포함
- TC-107 [E2E] 입력/예상결과/로그검증 포함
- TC-108 [E2E] 입력/예상결과/로그검증 포함
- TC-109 [E2E] 입력/예상결과/로그검증 포함
- TC-110 [E2E] 입력/예상결과/로그검증 포함
- TC-111 [E2E] 입력/예상결과/로그검증 포함
- TC-112 [E2E] 입력/예상결과/로그검증 포함
- TC-113 [E2E] 입력/예상결과/로그검증 포함
- TC-114 [E2E] 입력/예상결과/로그검증 포함
- TC-115 [E2E] 입력/예상결과/로그검증 포함
- TC-116 [E2E] 입력/예상결과/로그검증 포함
- TC-117 [E2E] 입력/예상결과/로그검증 포함
- TC-118 [E2E] 입력/예상결과/로그검증 포함
- TC-119 [E2E] 입력/예상결과/로그검증 포함
- TC-120 [E2E] 입력/예상결과/로그검증 포함
- TC-121 [Security] 입력/예상결과/로그검증 포함
- TC-122 [Security] 입력/예상결과/로그검증 포함
- TC-123 [Security] 입력/예상결과/로그검증 포함
- TC-124 [Security] 입력/예상결과/로그검증 포함
- TC-125 [Security] 입력/예상결과/로그검증 포함
- TC-126 [Security] 입력/예상결과/로그검증 포함
- TC-127 [Security] 입력/예상결과/로그검증 포함
- TC-128 [Security] 입력/예상결과/로그검증 포함
- TC-129 [Security] 입력/예상결과/로그검증 포함
- TC-130 [Security] 입력/예상결과/로그검증 포함
- TC-131 [Security] 입력/예상결과/로그검증 포함
- TC-132 [Security] 입력/예상결과/로그검증 포함
- TC-133 [Security] 입력/예상결과/로그검증 포함
- TC-134 [Security] 입력/예상결과/로그검증 포함
- TC-135 [Security] 입력/예상결과/로그검증 포함
- TC-136 [Security] 입력/예상결과/로그검증 포함
- TC-137 [Security] 입력/예상결과/로그검증 포함
- TC-138 [Security] 입력/예상결과/로그검증 포함
- TC-139 [Security] 입력/예상결과/로그검증 포함
- TC-140 [Security] 입력/예상결과/로그검증 포함
- TC-141 [Security] 입력/예상결과/로그검증 포함
- TC-142 [Security] 입력/예상결과/로그검증 포함
- TC-143 [Security] 입력/예상결과/로그검증 포함
- TC-144 [Security] 입력/예상결과/로그검증 포함
- TC-145 [Security] 입력/예상결과/로그검증 포함
- TC-146 [Security] 입력/예상결과/로그검증 포함
- TC-147 [Security] 입력/예상결과/로그검증 포함
- TC-148 [Security] 입력/예상결과/로그검증 포함
- TC-149 [Security] 입력/예상결과/로그검증 포함
- TC-150 [Security] 입력/예상결과/로그검증 포함
- TC-151 [Security] 입력/예상결과/로그검증 포함
- TC-152 [Security] 입력/예상결과/로그검증 포함
- TC-153 [Security] 입력/예상결과/로그검증 포함
- TC-154 [Security] 입력/예상결과/로그검증 포함
- TC-155 [Security] 입력/예상결과/로그검증 포함
- TC-156 [Security] 입력/예상결과/로그검증 포함
- TC-157 [Security] 입력/예상결과/로그검증 포함
- TC-158 [Security] 입력/예상결과/로그검증 포함
- TC-159 [Security] 입력/예상결과/로그검증 포함
- TC-160 [Security] 입력/예상결과/로그검증 포함
- TC-161 [Security] 입력/예상결과/로그검증 포함
- TC-162 [Security] 입력/예상결과/로그검증 포함
- TC-163 [Security] 입력/예상결과/로그검증 포함
- TC-164 [Security] 입력/예상결과/로그검증 포함
- TC-165 [Security] 입력/예상결과/로그검증 포함
- TC-166 [Security] 입력/예상결과/로그검증 포함
- TC-167 [Security] 입력/예상결과/로그검증 포함
- TC-168 [Security] 입력/예상결과/로그검증 포함
- TC-169 [Security] 입력/예상결과/로그검증 포함
- TC-170 [Security] 입력/예상결과/로그검증 포함
- TC-171 [Security] 입력/예상결과/로그검증 포함
- TC-172 [Security] 입력/예상결과/로그검증 포함
- TC-173 [Security] 입력/예상결과/로그검증 포함
- TC-174 [Security] 입력/예상결과/로그검증 포함
- TC-175 [Security] 입력/예상결과/로그검증 포함
- TC-176 [Security] 입력/예상결과/로그검증 포함
- TC-177 [Security] 입력/예상결과/로그검증 포함
- TC-178 [Security] 입력/예상결과/로그검증 포함
- TC-179 [Security] 입력/예상결과/로그검증 포함
- TC-180 [Security] 입력/예상결과/로그검증 포함
- TC-181 [Security] 입력/예상결과/로그검증 포함
- TC-182 [Security] 입력/예상결과/로그검증 포함
- TC-183 [Security] 입력/예상결과/로그검증 포함
- TC-184 [Security] 입력/예상결과/로그검증 포함
- TC-185 [Security] 입력/예상결과/로그검증 포함
- TC-186 [Security] 입력/예상결과/로그검증 포함
- TC-187 [Security] 입력/예상결과/로그검증 포함
- TC-188 [Security] 입력/예상결과/로그검증 포함
- TC-189 [Security] 입력/예상결과/로그검증 포함
- TC-190 [Security] 입력/예상결과/로그검증 포함
- TC-191 [Performance] 입력/예상결과/로그검증 포함
- TC-192 [Performance] 입력/예상결과/로그검증 포함
- TC-193 [Performance] 입력/예상결과/로그검증 포함
- TC-194 [Performance] 입력/예상결과/로그검증 포함
- TC-195 [Performance] 입력/예상결과/로그검증 포함
- TC-196 [Performance] 입력/예상결과/로그검증 포함
- TC-197 [Performance] 입력/예상결과/로그검증 포함
- TC-198 [Performance] 입력/예상결과/로그검증 포함
- TC-199 [Performance] 입력/예상결과/로그검증 포함
- TC-200 [Performance] 입력/예상결과/로그검증 포함
- TC-201 [Performance] 입력/예상결과/로그검증 포함
- TC-202 [Performance] 입력/예상결과/로그검증 포함
- TC-203 [Performance] 입력/예상결과/로그검증 포함
- TC-204 [Performance] 입력/예상결과/로그검증 포함
- TC-205 [Performance] 입력/예상결과/로그검증 포함
- TC-206 [Performance] 입력/예상결과/로그검증 포함
- TC-207 [Performance] 입력/예상결과/로그검증 포함
- TC-208 [Performance] 입력/예상결과/로그검증 포함
- TC-209 [Performance] 입력/예상결과/로그검증 포함
- TC-210 [Performance] 입력/예상결과/로그검증 포함
- TC-211 [Performance] 입력/예상결과/로그검증 포함
- TC-212 [Performance] 입력/예상결과/로그검증 포함
- TC-213 [Performance] 입력/예상결과/로그검증 포함
- TC-214 [Performance] 입력/예상결과/로그검증 포함
- TC-215 [Performance] 입력/예상결과/로그검증 포함
- TC-216 [Performance] 입력/예상결과/로그검증 포함
- TC-217 [Performance] 입력/예상결과/로그검증 포함
- TC-218 [Performance] 입력/예상결과/로그검증 포함
- TC-219 [Performance] 입력/예상결과/로그검증 포함
- TC-220 [Performance] 입력/예상결과/로그검증 포함
- TC-221 [Performance] 입력/예상결과/로그검증 포함
- TC-222 [Performance] 입력/예상결과/로그검증 포함
- TC-223 [Performance] 입력/예상결과/로그검증 포함
- TC-224 [Performance] 입력/예상결과/로그검증 포함
- TC-225 [Performance] 입력/예상결과/로그검증 포함
- TC-226 [Performance] 입력/예상결과/로그검증 포함
- TC-227 [Performance] 입력/예상결과/로그검증 포함
- TC-228 [Performance] 입력/예상결과/로그검증 포함
- TC-229 [Performance] 입력/예상결과/로그검증 포함
- TC-230 [Performance] 입력/예상결과/로그검증 포함
- TC-231 [Performance] 입력/예상결과/로그검증 포함
- TC-232 [Performance] 입력/예상결과/로그검증 포함
- TC-233 [Performance] 입력/예상결과/로그검증 포함
- TC-234 [Performance] 입력/예상결과/로그검증 포함
- TC-235 [Performance] 입력/예상결과/로그검증 포함
- TC-236 [Performance] 입력/예상결과/로그검증 포함
- TC-237 [Performance] 입력/예상결과/로그검증 포함
- TC-238 [Performance] 입력/예상결과/로그검증 포함
- TC-239 [Performance] 입력/예상결과/로그검증 포함
- TC-240 [Performance] 입력/예상결과/로그검증 포함

## 20. 부록 D. 샘플 정책 문구

### 20.1 개인정보 동의 문구
- 본 서비스는 Telegram 계정 식별정보를 로그인/이벤트 운영 목적으로 수집하며, 탈퇴 요청시 내부 정책에 따라 삭제 또는 비식별화 처리합니다.

### 20.2 보안 공지 문구
- 비정상 로그인 또는 토큰 재사용이 탐지될 경우, 보안을 위해 자동 로그아웃 후 재인증을 요청할 수 있습니다.

## 21. 결론

- 본 v2 계획서는 1차 문서의 UI/컴포넌트 강점을 유지하면서 인증, 데이터, 보안, 운영, 비용 관점을 production 수준으로 강화했다.
- 특히 로그인 인증 플로우와 users 중심 ERD를 우선 상세화했으며, 즉시 개발 가능한 SQL/TS 코드 예시를 포함했다.
- 다음 액션: 본 문서 승인 후 Phase A 착수(인증 + 기본 리스트)
