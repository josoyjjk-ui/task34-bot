# 불개미 이벤트 플랫폼 고도화 계획서 v4

> 기준 문서: `/Users/fireant/.openclaw/workspace/event-section-plan-v2.md`  
> 작성일: 2026-04-14  
> 목표: 운영 가능한 이벤트 플랫폼(참여 추적, 관리자 운영, 자동화 보상)으로 단계적 전환

---

## 1) 핵심 원칙

- 공통 일정은 **중복 표기 금지**. 동일 일정은 전체 화면에서 1회만 노출.
- 인프라 신규 도입 최소화: 기존 스택(Supabase + 대시보드) 우선 활용.
- 기능 추가 순서: 사용자 가치(참여 UX) → 운영 안정성(DB/관리자) → 자동화(지갑/보상).
- 각 Phase 종료 조건(DoD) 없으면 다음 Phase 진입 금지.

---

## 2) 현재 상태 요약 (v2 대비)

- v2는 인증/보안/ERD 방향은 좋지만, 실제 화면 UX와 운영 플로우가 분리되어 있음.
- 운영자가 매번 수동으로 이벤트/참여/보상을 관리해야 하는 병목 존재.
- 일정 데이터가 여러 블록에서 재사용되며 중복 표시가 발생할 여지 존재.

---

## 3) Phase 2 — 상세 페이지 + Galxe 스타일 UX (3일)

### 목표
- 이벤트 상세페이지 전환율 개선, 참여 CTA 명확화, 상태 가시성 강화.

### 작업 항목
1. 이벤트 상세 페이지 템플릿 표준화
- 섹션: 개요 / 참여조건 / 보상 / 일정 / FAQ / 참여버튼

2. 공통 일정 단일 표기 로직
- 일정 데이터는 `normalized_schedule` 1개 소스에서만 렌더
- 동일 `date+title+event_id`는 dedupe 처리 후 1건만 노출

3. Galxe 스타일 UX 체크리스트 적용
- 상단 히어로 + 진행 상태 배지(OPEN/CLOSED/ENDING)
- 미션 체크리스트(완료/미완료)
- 즉시 CTA(참여하기/지갑연결)
- 남은 시간 카운트다운
- 참여 혜택 카드 분리
- 모바일 우선 레이아웃(터치 영역 44px+)
- 로딩 스켈레톤/빈 상태/에러 상태 분리
- 이벤트 상태별 버튼 비활성화 규칙

### 산출물
- 이벤트 상세 UI 개편 완료
- 중복 일정 제거 로직 반영
- UX 체크리스트 8개 항목 충족 리포트

---

## 4) Phase 3 — DB + 관리자 + 참여 추적 (5일)

### 목표
- 운영자가 이벤트 생성/수정/종료/당첨 처리까지 대시보드에서 일괄 운영 가능.

### Supabase 스키마 (핵심)

#### `users`
- `id (uuid, pk)`
- `telegram_id (text, unique)`
- `wallet_address (text, nullable)`
- `display_name (text)`
- `role (text: member/admin/operator)`
- `created_at`, `updated_at`

#### `events`
- `id (uuid, pk)`
- `slug (text, unique)`
- `title (text)`
- `description (text)`
- `status (text: draft/open/closed/settled)`
- `start_at`, `end_at`
- `reward_policy (jsonb)`
- `created_by (uuid fk users.id)`
- `created_at`, `updated_at`

#### `participations`
- `id (uuid, pk)`
- `event_id (uuid fk events.id)`
- `user_id (uuid fk users.id)`
- `mission_state (jsonb)`  // 미션별 완료 여부
- `score (numeric)`
- `submitted_at`
- `unique(event_id, user_id)`

#### `rewards`
- `id (uuid, pk)`
- `event_id (uuid fk events.id)`
- `user_id (uuid fk users.id)`
- `reward_type (text)`
- `amount (numeric)`
- `status (text: pending/sent/failed)`
- `tx_hash (text, nullable)`
- `sent_at`

#### `audit_logs`
- `id (uuid, pk)`
- `actor_user_id (uuid fk users.id)`
- `action (text)` // create_event, edit_event, close_event, reward_send 등
- `target_type (text)` // event/user/reward
- `target_id (text)`
- `payload (jsonb)`
- `created_at`

### 관리자 기능
- 이벤트 CRUD
- 참여자 목록/검색/필터
- 참여 내역 CSV 내보내기
- 당첨자 추첨(규칙 기반)
- 보상 전송 상태 모니터링
- 감사 로그 조회

### 산출물
- Supabase 마이그레이션 SQL
- 관리자 화면(목록/상세/추첨/보상)
- 참여 추적 대시보드(일별/이벤트별)

---

## 5) Phase 4 — 자동화 + 지갑 연동 (6일)

### 목표
- 이벤트 등록부터 참여 검증, 보상 지급까지 반자동/자동 운영.

### 작업 항목
1. task34-bot 연동
- 이벤트 생성 시 플랫폼에 자동 반영
- 상태 변경(open→closed→settled) 동기화

2. 소셜 검증 자동화
- 텔레그램 채널 가입 확인
- 미션 검증 결과를 `participations.mission_state`에 반영

3. 지갑 연결
- MetaMask/WalletConnect 연결
- 사용자 계정과 wallet_address 매핑

4. 온체인 검증
- 지정 토큰 잔액/보유 여부 체크
- 조건 미달 시 보상 대상 자동 제외

5. 리워드 자동 분배
- 당첨자 리스트 확정 후 배치 전송
- 성공/실패 상태와 tx hash 기록

### 산출물
- bot→platform 자동 동기화
- 지갑/온체인 검증 파이프라인
- 자동 보상 배치 + 실패 재시도 큐

---

## 6) 핵심 API 명세 (요약)

### 이벤트
- `GET /api/events`
- `GET /api/events/:slug`
- `POST /api/events` (admin)
- `PATCH /api/events/:id` (admin)
- `POST /api/events/:id/close` (admin)

### 참여
- `POST /api/events/:id/participate`
- `GET /api/events/:id/participants` (admin/operator)
- `POST /api/events/:id/verify-social`
- `POST /api/events/:id/verify-wallet`

### 보상
- `POST /api/events/:id/draw` (admin)
- `POST /api/events/:id/rewards/dispatch` (admin)
- `GET /api/events/:id/rewards`

### 운영/감사
- `GET /api/admin/audit-logs`
- `GET /api/admin/metrics/events`

---

## 7) 리스크 및 완화책

| 리스크 | 영향 | 완화책 |
|---|---|---|
| 일정 중복 노출 재발 | UX 혼란, 신뢰 저하 | 일정 렌더 직전 dedupe + QA 체크리스트 강제 |
| 봇 동기화 지연 | 이벤트 반영 누락 | 재시도 큐 + dead-letter 로그 + 수동 재동기화 버튼 |
| 온체인 검증 장애 | 보상 오지급/지연 | 캐시 + 재검증 배치 + 수동 승인 단계 |
| 관리자 오작동(실수 종료/수정) | 운영 사고 | audit_logs + 롤백 API + 권한 분리 |
| 대량 참여 시 DB 부하 | 응답 지연 | 인덱스/페이지네이션/비동기 배치 처리 |

---

## 8) 일정표 (현실 산정)

| Phase | 기간 | 핵심 산출물 |
|---|---|---|
| Phase 2 | 4/15 ~ 4/17 (3일) | 상세페이지 + Galxe UX + 공통 일정 단일 표기 |
| Phase 3 | 4/18 ~ 4/24 (5일) | Supabase 스키마 + 관리자 + 참여 추적 |
| Phase 4 | 4/25 ~ 4/30 (6일) | bot 연동 + 지갑/온체인 검증 + 자동 보상 |

---

## 9) Definition of Done (DoD)

- 공통 일정이 화면에서 중복 없이 1회만 노출됨(테스트 케이스 5개 통과).
- 이벤트 생성→참여→검증→당첨→보상 흐름이 관리자 화면에서 재현 가능.
- 모든 관리자 액션이 `audit_logs`에 기록됨.
- 실패 시나리오(검증 실패, 전송 실패, 동기화 실패)별 복구 경로 문서화 완료.

---

## 10) 즉시 실행 순서

1. 일정 dedupe 로직을 먼저 패치 (중복 표시 즉시 제거)  
2. 이벤트 상세페이지 Galxe UX 체크리스트 반영  
3. Supabase 스키마 마이그레이션 적용  
4. 관리자 CRUD + 참여 추적 화면 연결  
5. task34-bot 동기화 및 보상 자동화 연결

