# 불개미 게시판 이벤트섹션 구현 계획서 v2

> 작성일: 2026-04-10 | v1 기반 + 작전장교 검토 피드백 10개 항목 전면 반영

---

## 1. 레퍼런스 핵심 요약

- **DOKDODAO**: 히어로 배너 → 4열 카드 그리드 → 전체/진행중/종료됨 3탭 필터 + 검색 + 페이지네이션. 다크테마.
- **Galxe**: 좌(퀘스트 설명+참여조건 체크리스트) / 우(보상+참여버튼). 하단에 관련 퀘스트 카드.
- **핵심 패턴**: 탭 필터 상태 구분, 카드에 핵심 정보 요약, 체크리스트 참여 가이드, 종료 이벤트 검색 가능 아카이빙.

---

## 2. 로그인/인증 플로우 (신규 — 최우선)

### 2.1 인증 방식 선택

| Phase | 방식 | 설명 |
|-------|------|------|
| MVP~Phase 2 | **텔레그램 Login Widget** | 기존 커뮤니티 유저 즉시 연동, 추가 가입 불필요 |
| Phase 3 | **+ 지갑 로그인 (SIWE)** | MetaMask/WalletConnect 옵션 추가 |
| 보조 | **구글 OAuth** | 텔레그램 없는 유저용 fallback |

### 2.2 텔레그램 OAuth 플로우 (상세)

```
[유저]                    [프론트엔드]                [Cloudflare Worker API]
  │                           │                              │
  ├── 텔레그램 로그인 클릭 ──→│                              │
  │                           ├── TG Login Widget 표시 ──→   │
  │                           │                              │
  ├── 텔레그램 승인 ─────────→│                              │
  │                           │   (TG → redirect with params)│
  │                           ├── POST /api/auth/telegram ──→│
  │                           │   {id, first_name, username, │
  │                           │    photo_url, auth_date, hash}│
  │                           │                              │
  │                           │                   ┌──────────┤
  │                           │                   │ 1) HMAC-SHA256 서명 검증
  │                           │                   │    key = SHA256(BOT_TOKEN)
  │                           │                   │    data = sorted params
  │                           │                   │    compare hash
  │                           │                   │ 2) auth_date < 5분 체크
  │                           │                   │ 3) users upsert
  │                           │                   │ 4) JWT 발급
  │                           │                   └──────────┤
  │                           │                              │
  │                           │←── Set-Cookie: access_token  │
  │                           │    (httpOnly, Secure,        │
  │                           │     SameSite=Strict, 15min)  │
  │                           │←── Set-Cookie: refresh_token │
  │                           │    (httpOnly, Secure,        │
  │                           │     SameSite=Strict, 7days)  │
  │                           │                              │
  ├── 로그인 완료 ←──────────│                              │
```

### 2.3 API 엔드포인트 명세

| 엔드포인트 | 메서드 | 인증 | 설명 |
|-----------|--------|------|------|
| `/api/auth/telegram` | POST | 없음 | TG 서명 검증 → JWT 발급 → 쿠키 세팅 |
| `/api/auth/refresh` | POST | refresh_token | access_token 갱신 + refresh_token 회전 |
| `/api/auth/logout` | POST | access_token | 토큰 블랙리스트 + 쿠키 삭제 |
| `/api/auth/me` | GET | access_token | 현재 유저 정보 반환 |
| `/api/events` | GET | 없음 | 이벤트 목록 (공개) |
| `/api/events/:id` | GET | 없음 | 이벤트 상세 (공개) |
| `/api/events/:id/participants` | GET | 없음 | 참여자 목록 (닉네임 마스킹) |
| `/api/participate` | POST | access_token | 이벤트 참여 등록 |
| `/api/me/events` | GET | access_token | 내 참여 현황 |
| `/api/me/delete` | POST | access_token | 계정 삭제 요청 |
| `/api/admin/events` | POST/PUT/DELETE | admin_token | 이벤트 CRUD |
| `/api/admin/participants` | GET/PUT | admin_token | 참여자 관리 |
| `/api/admin/events/import` | POST | admin_token | CSV 일괄 업로드 |

### 2.4 인증 미들웨어 코드

```typescript
// auth/middleware.ts
import { z } from 'zod';
import * as jose from 'jose';

const JWT_SECRET = new TextEncoder().encode(env.JWT_SECRET);
const ACCESS_TTL = '15m';
const REFRESH_TTL = '7d';

// 텔레그램 서명 검증
export async function verifyTelegramAuth(params: Record<string, string>, botToken: string): Promise<boolean> {
  const { hash, ...data } = params;
  
  // auth_date 5분 이내 체크
  const authDate = parseInt(data.auth_date);
  if (Date.now() / 1000 - authDate > 300) return false;
  
  // HMAC-SHA256 검증
  const secretKey = await crypto.subtle.importKey(
    'raw',
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(botToken)),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  const checkString = Object.keys(data)
    .sort()
    .map(k => `${k}=${data[k]}`)
    .join('\n');
  
  const signature = await crypto.subtle.sign(
    'HMAC',
    secretKey,
    new TextEncoder().encode(checkString)
  );
  
  const hexHash = Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  
  return hexHash === hash;
}

// JWT 발급
export async function issueTokens(userId: string, role: string) {
  const accessToken = await new jose.SignJWT({ sub: userId, role })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime(ACCESS_TTL)
    .setIssuedAt()
    .sign(JWT_SECRET);
    
  const refreshToken = await new jose.SignJWT({ sub: userId, type: 'refresh' })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime(REFRESH_TTL)
    .setIssuedAt()
    .setJti(crypto.randomUUID()) // 회전용 jti
    .sign(JWT_SECRET);
    
  return { accessToken, refreshToken };
}

// 인증 미들웨어
export async function authMiddleware(request: Request, env: Env): Promise<{ userId: string; role: string } | null> {
  const cookie = request.headers.get('Cookie') || '';
  const match = cookie.match(/access_token=([^;]+)/);
  if (!match) return null;
  
  try {
    const { payload } = await jose.jwtVerify(match[1], JWT_SECRET);
    
    // 블랙리스트 체크
    const blacklisted = await env.DB.prepare(
      'SELECT 1 FROM token_blacklist WHERE jti = ?'
    ).bind(payload.jti).first();
    if (blacklisted) return null;
    
    return { userId: payload.sub as string, role: payload.role as string };
  } catch {
    return null;
  }
}

// 쿠키 세팅 헬퍼
export function setAuthCookies(accessToken: string, refreshToken: string): Headers {
  const headers = new Headers();
  headers.append('Set-Cookie', 
    `access_token=${accessToken}; HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=900`);
  headers.append('Set-Cookie',
    `refresh_token=${refreshToken}; HttpOnly; Secure; SameSite=Strict; Path=/api/auth; Max-Age=604800`);
  return headers;
}
```

### 2.5 JWT 정책

| 항목 | 값 | 설명 |
|------|------|------|
| access_token TTL | 15분 | 짧게 유지 → 탈취 피해 최소화 |
| refresh_token TTL | 7일 | 자동 로그인 |
| 저장 위치 | httpOnly + Secure + SameSite=Strict 쿠키 | XSS로 탈취 불가 |
| 토큰 회전 | refresh 사용 시 새 refresh 발급 + 이전 jti 블랙리스트 | 재사용 공격 방지 |
| 로그아웃 | access_token jti 블랙리스트 + 쿠키 삭제 | 즉시 무효화 |

---

## 3. 유저 데이터 저장 / DB ERD (신규 — 최우선)

### 3.1 ERD (Entity Relationship Diagram)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   users      │     │   events     │     │   conditions    │
├─────────────┤     ├──────────────┤     ├─────────────────┤
│ id (PK)     │     │ id (PK)      │     │ id (PK)         │
│ telegram_id │     │ slug         │     │ event_id (FK)   │
│ tg_username │     │ title        │     │ sort_order      │
│ tg_photo    │     │ description  │     │ type            │
│ nickname    │     │ long_desc    │     │ platform        │
│ email       │     │ banner_image │     │ label           │
│ wallet_addr │     │ thumb_image  │     │ url             │
│ role        │     │ badge_label  │     │ auto_verify     │
│ points      │     │ badge_color  │     │ created_at      │
│ status      │     │ status       │     └─────────────────┘
│ source      │     │ start_date   │
│ metadata    │     │ end_date     │     ┌─────────────────────┐
│ created_at  │     │ reward_type  │     │ participant_events  │
│ updated_at  │     │ reward_amt   │     ├─────────────────────┤
│ last_login  │     │ reward_unit  │     │ id (PK)             │
│ deleted_at  │     │ max_parts    │     │ participant_id (FK) │
│ version     │     │ category     │     │ event_type          │
└──────┬──────┘     │ tags         │     │ old_status          │
       │            │ version      │     │ new_status          │
       │            │ deleted_at   │     │ changed_by          │
       │            │ created_at   │     │ reason              │
       │            │ updated_at   │     │ created_at          │
       │            │ published_at │     └─────────────────────┘
       │            └──────┬───────┘
       │                   │
       │    ┌──────────────┴──────────────┐
       │    │       participants          │
       │    ├─────────────────────────────┤
       │    │ id (PK)                     │
       ├───→│ user_id (FK → users)        │
       │    │ event_id (FK → events)      │
       │    │ idempotency_key (UNIQUE)    │
       │    │ status                      │
       │    │ progress (JSON)             │
       │    │ source                      │
       │    │ reward_claimed              │
       │    │ metadata (JSON)             │
       │    │ version                     │
       │    │ deleted_at                  │
       │    │ joined_at                   │
       │    │ completed_at               │
       │    │ UNIQUE(event_id, user_id)   │
       │    └─────────────────────────────┘
       │
       │    ┌─────────────────────┐    ┌──────────────────────┐
       │    │   consents          │    │  deletion_requests   │
       │    ├─────────────────────┤    ├──────────────────────┤
       ├───→│ id (PK)             │    │ id (PK)              │
       │    │ user_id (FK)        │    │ user_id (FK)         │
       │    │ consent_type        │    │ status               │
       │    │ granted             │    │ requested_at         │
       │    │ ip_address          │    │ processed_at         │
       │    │ user_agent          │    │ processed_by         │
       │    │ created_at          │    └──────────────────────┘
       │    └─────────────────────┘
       │
       │    ┌─────────────────────┐    ┌──────────────────────┐
       │    │   audit_logs        │    │  token_blacklist     │
       │    ├─────────────────────┤    ├──────────────────────┤
       ├───→│ id (PK)             │    │ jti (PK)             │
            │ user_id (FK)        │    │ expires_at           │
            │ action              │    │ created_at           │
            │ resource_type       │    └──────────────────────┘
            │ resource_id         │
            │ details (JSON)      │    ┌──────────────────────┐
            │ ip_address          │    │  verification_logs   │
            │ created_at          │    ├──────────────────────┤
            └─────────────────────┘    │ id (PK)              │
                                       │ participant_id (FK)  │
                                       │ condition_id (FK)    │
                                       │ method               │
                                       │ result               │
                                       │ evidence (JSON)      │
                                       │ verified_by          │
                                       │ created_at           │
                                       └──────────────────────┘
```

### 3.2 DB 마이그레이션 SQL

```sql
-- migrations/001_initial.sql

-- ====== USERS ======
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  telegram_id TEXT UNIQUE,
  tg_username TEXT,
  tg_photo_url TEXT,
  nickname TEXT NOT NULL,
  email TEXT,
  wallet_address TEXT,
  role TEXT DEFAULT 'user' CHECK(role IN ('user','editor','admin','owner')),
  points INTEGER DEFAULT 0,
  status TEXT DEFAULT 'active' CHECK(status IN ('active','suspended','deleted')),
  source TEXT DEFAULT 'telegram',  -- 유입 경로: telegram, wallet, google, manual
  metadata TEXT DEFAULT '{}',      -- 확장 가능 JSON
  version INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  last_login_at TEXT,
  deleted_at TEXT                   -- soft delete
);

-- ====== EVENTS ======
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  long_description TEXT,
  banner_image TEXT,
  thumbnail_image TEXT,
  badge_label TEXT,
  badge_color TEXT DEFAULT '#FF4444',
  status TEXT DEFAULT 'draft' CHECK(status IN ('draft','review','upcoming','active','ended','archived')),
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  reward_type TEXT,
  reward_amount INTEGER DEFAULT 0,
  reward_unit TEXT DEFAULT 'P',
  reward_description TEXT,
  max_participants INTEGER,
  category TEXT,
  tags TEXT DEFAULT '[]',          -- JSON array
  version INTEGER DEFAULT 1,
  deleted_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  published_at TEXT                 -- 예약 발행 지원
);

-- ====== CONDITIONS ======
CREATE TABLE IF NOT EXISTS conditions (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  sort_order INTEGER DEFAULT 0,
  type TEXT NOT NULL,
  platform TEXT,
  label TEXT NOT NULL,
  url TEXT,
  auto_verify INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== PARTICIPANTS ======
CREATE TABLE IF NOT EXISTS participants (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  idempotency_key TEXT UNIQUE,     -- 중복 참여 방지
  status TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress','completed','disqualified','withdrawn')),
  progress TEXT DEFAULT '{}',      -- JSON: 조건별 완료 상태
  source TEXT DEFAULT 'web',       -- 유입 경로: web, telegram_bot, admin_manual
  reward_claimed INTEGER DEFAULT 0,
  metadata TEXT DEFAULT '{}',      -- 확장 JSON
  version INTEGER DEFAULT 1,
  deleted_at TEXT,
  joined_at TEXT DEFAULT (datetime('now')),
  completed_at TEXT,
  UNIQUE(event_id, user_id)
);

-- ====== CONSENTS (개인정보 동의) ======
CREATE TABLE IF NOT EXISTS consents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  consent_type TEXT NOT NULL,      -- 'privacy_policy', 'marketing', 'data_collection'
  granted INTEGER NOT NULL,        -- 1=동의, 0=철회
  ip_address TEXT,
  user_agent TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== AUDIT LOGS ======
CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  action TEXT NOT NULL,            -- 'login','participate','admin_update','delete_request'
  resource_type TEXT,              -- 'event','participant','user'
  resource_id TEXT,
  details TEXT DEFAULT '{}',
  ip_address TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== DELETION REQUESTS ======
CREATE TABLE IF NOT EXISTS deletion_requests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  status TEXT DEFAULT 'pending' CHECK(status IN ('pending','processing','completed','rejected')),
  requested_at TEXT DEFAULT (datetime('now')),
  processed_at TEXT,
  processed_by TEXT
);

-- ====== TOKEN BLACKLIST ======
CREATE TABLE IF NOT EXISTS token_blacklist (
  jti TEXT PRIMARY KEY,
  expires_at TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== VERIFICATION LOGS ======
CREATE TABLE IF NOT EXISTS verification_logs (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  condition_id TEXT NOT NULL REFERENCES conditions(id),
  method TEXT NOT NULL,            -- 'auto_api', 'manual_admin', 'user_screenshot'
  result TEXT NOT NULL,            -- 'pass', 'fail', 'pending'
  evidence TEXT DEFAULT '{}',      -- JSON: 스크린샷 URL, API 응답 등
  verified_by TEXT,                -- user_id (관리자) or 'system'
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== PARTICIPANT EVENTS (상태 변경 이력) ======
CREATE TABLE IF NOT EXISTS participant_events (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,        -- 'joined','condition_completed','status_changed','reward_claimed'
  old_status TEXT,
  new_status TEXT,
  changed_by TEXT,                 -- user_id or 'system'
  reason TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- ====== INDEXES ======
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_dates ON events(start_date, end_date);
CREATE INDEX idx_participants_event ON participants(event_id);
CREATE INDEX idx_participants_user ON participants(user_id);
CREATE INDEX idx_participants_status ON participants(status);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_blacklist_expires ON token_blacklist(expires_at);
```

### 3.3 개인정보 처리방침

| 항목 | 내용 |
|------|------|
| **수집 항목** | 텔레그램 ID, 사용자명, 프로필 사진 URL, 닉네임, 지갑주소(선택) |
| **수집 목적** | 이벤트 참여 관리, 보상 지급, 서비스 개선 |
| **보관 기간** | 회원 탈퇴 후 30일 (법적 의무 보관 제외) |
| **제3자 제공** | 없음 (이벤트 파트너에 익명 통계만 제공) |
| **삭제 프로세스** | `/api/me/delete` → 30일 유예 → soft delete → 90일 후 hard delete |
| **동의 철회** | 마이페이지에서 언제든 철회 가능, 즉시 관련 데이터 처리 중단 |
| **문의** | fireantcrypto@gmail.com |

---

## 4. 보안 기준선 (신규)

### 4.1 API 인증/인가 매트릭스

| 엔드포인트 | guest | user | editor | admin | owner |
|-----------|-------|------|--------|-------|-------|
| GET /api/events | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /api/events/:id | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /api/events/:id/participants | ✅* | ✅ | ✅ | ✅ | ✅ |
| POST /api/participate | ❌ | ✅ | ✅ | ✅ | ✅ |
| GET /api/me/events | ❌ | ✅ | ✅ | ✅ | ✅ |
| POST /api/me/delete | ❌ | ✅ | ✅ | ✅ | ✅ |
| POST /api/admin/events | ❌ | ❌ | ✅ | ✅ | ✅ |
| PUT /api/admin/events/:id | ❌ | ❌ | ✅ | ✅ | ✅ |
| DELETE /api/admin/events/:id | ❌ | ❌ | ❌ | ✅ | ✅ |
| GET /api/admin/participants | ❌ | ❌ | ✅ | ✅ | ✅ |
| PUT /api/admin/participants/:id | ❌ | ❌ | ❌ | ✅ | ✅ |
| POST /api/admin/events/import | ❌ | ❌ | ❌ | ✅ | ✅ |
| RBAC 관리 | ❌ | ❌ | ❌ | ❌ | ✅ |

*guest는 닉네임 마스킹 버전만 열람

### 4.2 보안 체크리스트

```
✅ Prepared statements 강제 (SQL injection 방지)
✅ Zod 스키마 검증 (모든 API 입력)
✅ Cloudflare Rate Limiting (100 req/min/IP)
✅ Cloudflare Turnstile (참여 등록 시 봇 방지)
✅ CSP 헤더: script-src 'self'; style-src 'self' 'unsafe-inline'
✅ HSTS: max-age=31536000; includeSubDomains
✅ X-Frame-Options: DENY
✅ X-Content-Type-Options: nosniff
✅ CSRF: SameSite=Strict 쿠키 + Origin 헤더 검증
✅ XSS: DOMPurify로 유저 입력 sanitize
```

### 4.3 Zod 스키마 예시

```typescript
import { z } from 'zod';

export const ParticipateSchema = z.object({
  eventId: z.string().min(1).max(50),
  idempotencyKey: z.string().uuid(),
  conditions: z.record(z.string(), z.boolean()).optional(),
}).strict();

export const EventCreateSchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/).min(3).max(100),
  title: z.string().min(1).max(200),
  description: z.string().max(1000).optional(),
  longDescription: z.string().max(10000).optional(),
  startDate: z.string().datetime(),
  endDate: z.string().datetime(),
  rewardType: z.enum(['points', 'token', 'nft', 'custom']),
  rewardAmount: z.number().int().min(0),
  rewardUnit: z.string().max(10),
  category: z.string().max(50).optional(),
  tags: z.array(z.string().max(30)).max(10).optional(),
  maxParticipants: z.number().int().min(1).nullable().optional(),
}).strict();

export const TelegramAuthSchema = z.object({
  id: z.number(),
  first_name: z.string(),
  last_name: z.string().optional(),
  username: z.string().optional(),
  photo_url: z.string().url().optional(),
  auth_date: z.number(),
  hash: z.string().length(64),
}).strict();
```

---

## 5. 비용/스케일링 시나리오 (신규)

### 5.1 Cloudflare 무료 플랜 한계

| 리소스 | 무료 한계 | 1K MAU | 10K MAU | 50K MAU |
|--------|----------|--------|---------|---------|
| Worker 요청 | 100K/일 | ~3K/일 ✅ | ~30K/일 ✅ | ~150K/일 ⚠️ |
| D1 읽기 | 5M/일 | ~10K/일 ✅ | ~100K/일 ✅ | ~500K/일 ✅ |
| D1 쓰기 | 100K/일 | ~500/일 ✅ | ~5K/일 ✅ | ~25K/일 ✅ |
| D1 저장 | 5GB | ~50MB ✅ | ~500MB ✅ | ~2GB ✅ |
| R2 저장 | 10GB | ~1GB ✅ | ~5GB ✅ | ~20GB ⚠️ |

### 5.2 임계치 알람 및 대응

| 임계치 | 상태 | 대응 |
|--------|------|------|
| Worker 70K/일 | ⚠️ 경고 | 캐시 적극 활용, 정적 페이지 확대 |
| Worker 90K/일 | 🔴 위험 | Cloudflare Workers Paid ($5/월) 전환 |
| D1 3GB | ⚠️ 경고 | 오래된 audit_logs, token_blacklist 정리 |
| D1 4.5GB | 🔴 위험 | Turso 전환 검토 (무료 8GB) |
| 50K MAU 돌파 | 📈 성장 | Vercel Pro + Turso Pro 전환 (~$40/월) |

### 5.3 캐시 전략

```
정적 자산 (이미지/CSS/JS) → Cloudflare CDN (365일)
이벤트 목록 API → KV 캐시 (5분 TTL)
이벤트 상세 API → KV 캐시 (1분 TTL)
참여자 수 → KV 캐시 (30초 TTL)
인증 API → 캐시 없음
```

---

## 6. 마이그레이션 Runbook (신규)

### 6.1 소스별 필드 매핑

| 소스 | 소스 필드 | → DB 필드 | 변환 |
|------|----------|----------|------|
| **구글폼** | 타임스탬프 | participants.joined_at | ISO8601 변환 |
| | 텔레그램 닉네임 | users.nickname | trim, lowercase |
| | 텔레그램 ID | users.telegram_id | 숫자 추출 |
| | 지갑주소 | users.wallet_address | 0x prefix 검증 |
| | 이벤트명 | participants.event_id | slug 매핑 테이블 참조 |
| **텔레그램봇 DB** | user_id | users.telegram_id | 직접 매핑 |
| | username | users.tg_username | @ 제거 |
| | referral_code | users.metadata.referral | JSON 필드 |
| | points | users.points | 합산 |
| **리더보드 JSON** | rank | (계산) | points 기준 재계산 |
| | score | users.points | 합산/최대값 선택 |

### 6.2 Dedupe 규칙

```
1차 키: telegram_id (가장 신뢰)
2차 키: tg_username (telegram_id 없을 시)
3차 키: wallet_address (유저 매칭 보조)
충돌 시: 최신 레코드 우선 + 수동 검토 큐
```

### 6.3 ETL 프로세스

```
1. EXTRACT  — 구글폼 CSV export, 봇 DB sqlite dump, 리더보드 JSON
2. TRANSFORM — 필드 매핑, 중복 제거, 데이터 정제, ID 생성
3. LOAD (dry-run) — D1 테스트 DB에 적재, 검증 쿼리 실행
4. VERIFY — 레코드 수 비교, 샘플 10% 수동 검증, 불일치 리포트
5. LOAD (production) — 본 DB에 적재
6. POST-CHECK — 총 유저수, 참여 수, 포인트 합계 교차 검증
```

### 6.4 롤백

```sql
-- 마이그레이션 전 백업
.dump > backup_pre_migration.sql

-- 롤백 시
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS users;
-- ... (모든 테이블)
.read backup_pre_migration.sql
```

---

## 7. 운영 백오피스 (신규)

### 7.1 RBAC (역할 기반 접근 제어)

| 역할 | 이벤트 열람 | 이벤트 생성 | 이벤트 발행 | 참여자 관리 | 유저 관리 | RBAC 변경 |
|------|-----------|-----------|-----------|-----------|----------|----------|
| owner | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| editor | ✅ | ✅ | ❌ (승인 필요) | 열람만 | ❌ | ❌ |
| reviewer | ✅ | ❌ | 승인/반려만 | 열람만 | ❌ | ❌ |

### 7.2 이벤트 발행 플로우

```
Editor: draft 작성 → review 요청
  ↓
Reviewer/Admin: review → approve (→ upcoming/active) or reject (→ draft + 피드백)
  ↓
System: start_date 도달 → active 자동 전환
  ↓
System: end_date 도달 → ended 자동 전환
  ↓
Admin: ended → archived (수동)
```

### 7.3 관리 기능

- **CSV Import**: 참여자 일괄 등록 (구글폼 export → 관리자 페이지에서 업로드)
- **예약 발행**: published_at 필드로 미래 시점 자동 발행
- **변경 이력**: audit_logs로 모든 변경 추적, 이전 버전 복원 가능 (version 필드)
- **일괄 상태 변경**: 이벤트 종료 시 미완료 참여자 일괄 처리

---

## 8. 모바일 UX 상태 정의 (신규)

### 8.1 추가 컴포넌트

| 컴포넌트 | 용도 | 트리거 |
|----------|------|--------|
| `AuthGate` | 로그인 필요 액션 시 로그인 모달 표시 | 미인증 유저가 참여 클릭 |
| `EmptyState` | "이벤트가 없습니다" + CTA | 필터 결과 0건 |
| `ErrorState` | "로딩 실패" + 재시도 버튼 | API 에러 |
| `Skeleton` | 카드/리스트 로딩 플레이스홀더 | 데이터 로딩 중 |
| `PrivacyMask` | 닉네임 부분 마스킹 (cry***_kim) | 비로그인 참여자 목록 |
| `MobileCTA` | 하단 고정 참여하기 버튼 | 모바일 상세 페이지 |

### 8.2 모바일 레이아웃

```
데스크톱: 좌(이벤트 정보) | 우(사이드바)
모바일:   상(이벤트 정보) → 하(사이드바 내용 인라인) + 하단 고정 CTA

카드 그리드:
  데스크톱: 4열
  태블릿: 2열
  모바일: 1열 (스와이프 캐러셀 옵션)
```

---

## 9. 불개미만의 차별점 / USP (신규)

### 9.1 차별화 기능 3가지

| # | 기능 | 설명 | DOKDODAO/Galxe 대비 |
|---|------|------|---------------------|
| 1 | **게시판 연계 미션** | 불개미 게시판에 글 작성 = 참여 조건 자동 검증 | 외부 플랫폼은 자체 게시판 없음 |
| 2 | **콘텐츠 품질 점수** | 게시글 좋아요/댓글 수 기반 보상 가중치 | 단순 참여 여부만 체크하는 경쟁사 대비 품질 인센티브 |
| 3 | **이벤트 학습 아카이브** | 종료된 이벤트를 프로젝트별/시기별로 탐색, "이 프로젝트의 이전 이벤트" 연결 | 대부분 종료 이벤트는 숨김 처리 |

추가 USP:
- **한국어 커뮤니티 큐레이션**: 한국어 네이티브 UX, 한국 시간대 기준 이벤트
- **텔레그램 원클릭**: 지갑 없이 텔레그램만으로 참여 (진입장벽 최소)
- **불개미 포인트 생태계**: 이벤트 참여 → 포인트 적립 → 리더보드 → 추가 보상

### 9.2 KPI

| 지표 | 목표 (3개월) | 측정 방법 |
|------|-------------|----------|
| 이벤트 참여율 | 커뮤니티 멤버 중 30% | 참여자 / 전체 유저 |
| 재참여율 | 60% | 2회 이상 참여 유저 비율 |
| 이벤트 완료율 | 70% | completed / total participants |
| 전환율 (열람→참여) | 15% | 참여자 / 상세 페이지 방문자 |
| NPS | +50 | 분기별 설문 |

---

## 10. 구현 로드맵 (v1에서 유지 + 보강)

### Phase 1: MVP (1주, ~40h)
- Astro + React 프로젝트 셋업
- EventCard, FilterTabs, SearchBar, Pagination, HeroBanner
- 이벤트 리스트 + 상세 페이지 (정적 JSON)
- EmptyState, ErrorState, Skeleton 컴포넌트
- 반응형 (4→2→1열), 모바일 CTA
- 과거 이벤트 데이터 수동 입력
- 참여는 기존 구글폼 링크 연결

### Phase 2: 참여자 데이터 + 로그인 (2주, ~70h)
- Cloudflare Worker API + D1 DB 구축 (위 스키마)
- 텔레그램 로그인 연동 (HMAC 검증 + JWT)
- AuthGate, PrivacyMask 컴포넌트
- 참여 등록 플로우 (Turnstile 봇 방지)
- ParticipantList + Checklist (동적)
- 관리자 백오피스 (이벤트 CRUD + RBAC)
- 마이그레이션 ETL 실행
- 개인정보 처리방침 페이지

### Phase 3: 지갑 + 자동화 (3주, ~80h)
- MetaMask/WalletConnect 로그인 추가
- 온체인 조건 자동 검증
- Twitter/텔레그램 자동 검증
- 게시판 연계 미션 자동 검증
- 리워드 자동 분배
- 유저 대시보드 (내 참여 이력, 포인트)
- 알림 시스템 (이벤트 시작/마감)

### 총 예상 공수

| Phase | 기간 | 시간 | 비용 |
|-------|------|------|------|
| Phase 1 (MVP) | 1주 | ~40h | 무료 (GitHub Pages) |
| Phase 2 (참여자+로그인) | 2주 | ~70h | 무료 (Cloudflare 무료) |
| Phase 3 (지갑+자동화) | 3주 | ~80h | ~$5/월 (Workers Paid) |
| **합계** | **6주** | **~190h** | **$0~5/월** |

---

## 11. 배포/장애 대응 (신규)

### 배포 파이프라인
```
main push → GitHub Actions → Astro build → GitHub Pages (정적)
                           → Wrangler deploy (Cloudflare Worker API)
```

### 백업
- D1 DB: 일 1회 자동 export → R2 저장 (7일 보관)
- 코드: GitHub (자동)

### SLO
- 가용성: 99.5% (Cloudflare 인프라 의존)
- API 응답: p95 < 500ms
- 장애 대응: 15분 내 인지, 1시간 내 복구

---

*이 문서는 v1 + 작전장교 10개 피드백 전면 반영 2차 계획서입니다.*
*실제 개발 시작 전 해병님 리뷰 후 확정합니다.*
