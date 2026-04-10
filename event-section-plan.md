# 불개미 게시판 이벤트섹션 구현 계획서

> 작성일: 2026-04-10 | 작성자: ops subagent

---

## 1. 레퍼런스 핵심 요약

- **DOKDODAO**: 히어로 배너 슬라이더 → 진행중 이벤트 4열 카드 그리드 → 전체/진행중/종료됨 3탭 필터 + 검색 + 페이지네이션. 카드에 배지+썸네일+제목+남은시간+참여자수+보상금액. 다크테마 기반.
- **Galxe**: 이벤트 상세페이지 좌측(제목+설명+참여조건+보상) / 우측(참여버튼). 참여조건을 체크리스트 UI로 표시. 하단에 관련 퀘스트 카드 그리드.
- **핵심 패턴**: 탭 필터로 상태 구분, 카드에 핵심 정보 요약, 상세에서 체크리스트로 참여 가이드, 종료 이벤트도 검색 가능하게 아카이빙.

---

## 2. 페이지 구조 와이어프레임

### 2.1 메인 페이지 (이벤트 리스트)

```
┌──────────────────────────────────────────────────────────────┐
│  🔥 불개미  [홈] [이벤트] [리더보드] [커뮤니티]    [로그인] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              히어로 배너 (슬라이더)                   │    │
│  │  [이번주 이벤트] 덧글 작성하고 포인트 받자!          │    │
│  │               [참여하기 →]                           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ── 진행 중인 이벤트 ──────────────────────────────────      │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 🔴 LIVE  │ │ 🔴 LIVE  │ │ 🔴 LIVE  │ │ 🔴 LIVE  │        │
│  │          │ │          │ │          │ │          │        │
│  │ [이미지] │ │ [이미지] │ │ [이미지] │ │ [이미지] │        │
│  │          │ │          │ │          │ │          │        │
│  │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │        │
│  │ ⏰ 3일남 │ │ ⏰ 5일남 │ │ ⏰ 7일남 │ │ ⏰ 2일남 │        │
│  │ 👥 142명 │ │ 👥 89명  │ │ 👥 203명 │ │ 👥 56명  │        │
│  │ 💰 50P   │ │ 💰 100P  │ │ 💰 30P   │ │ 💰 200P  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
│  ── [전체] [진행중] [종료됨] ─── 🔍 검색 ──────────────      │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 종료됨   │ │ 종료됨   │ │ 진행중   │ │ 진행중   │        │
│  │ [이미지] │ │ [이미지] │ │ [이미지] │ │ [이미지] │        │
│  │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │        │
│  │ 👥 320명 │ │ 👥 415명 │ │ 👥 78명  │ │ 👥 112명 │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │        < 1  2  3  4  5 >   페이지네이션              │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  © 2026 FireAnt Crypto                                       │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 이벤트 상세 페이지

```
┌──────────────────────────────────────────────────────────────┐
│  🔥 불개미  [홈] [이벤트] [리더보드] [커뮤니티]    [로그인] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ← 이벤트 목록으로                                           │
│                                                              │
│  ┌─────────────────────────────┐ ┌────────────────────┐      │
│  │                             │ │                    │      │
│  │  [이벤트 배너 이미지]       │ │  🔴 진행 중        │      │
│  │                             │ │                    │      │
│  │  이벤트 제목                │ │  ⏰ 마감: 3일 남음 │      │
│  │  ==============            │ │  👥 참여자: 142명  │      │
│  │                             │ │  💰 보상: 50 포인트│      │
│  │  이벤트 설명 텍스트         │ │                    │      │
│  │  이벤트 설명 텍스트         │ │  ┌──────────────┐  │      │
│  │  ...                        │ │  │ 참여하기 ✋  │  │      │
│  │                             │ │  └──────────────┘  │      │
│  │  ── 참여 조건 ──           │ │                    │      │
│  │                             │ │  참여 방법 안내   │      │
│  │  ☑ 텔레그램 채널 팔로우    │ │  텍스트...        │      │
│  │  ☐ 트위터 리트윗           │ │                    │      │
│  │  ☐ 디스코드 가입           │ │                    │      │
│  │  ☐ 커뮤니티 게시글 작성    │ │                    │      │
│  │                             │ │                    │      │
│  └─────────────────────────────┘ └────────────────────┘      │
│                                                              │
│  ── 참여자 명단 (142명) ── [전체] [완료] [진행중] ────      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ #  │ 닉네임      │ 참여일      │ 상태    │ 진행도   │    │
│  │────┼─────────────┼─────────────┼─────────┼──────────│    │
│  │ 1  │ fire_ant_01 │ 2026-04-08  │ ✅ 완료 │ 4/4      │    │
│  │ 2  │ crypto_kim  │ 2026-04-08  │ 🔄 진행 │ 2/4      │    │
│  │ 3  │ defi_whale  │ 2026-04-09  │ 🔄 진행 │ 3/4      │    │
│  │ 4  │ ...         │ ...         │ ...     │ ...      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ── 다른 이벤트 ──────────────────────────────────────      │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ [이미지] │ │ [이미지] │ │ [이미지] │ │ [이미지] │        │
│  │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │ │ 이벤트명 │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 컴포넌트 분해

### 3.1 컴포넌트 트리

```
App
├── Header (네비게이션)
├── EventListPage (메인)
│   ├── HeroBanner (슬라이더)
│   ├── ActiveEventsSection
│   │   └── EventCard[] (진행중 이벤트)
│   ├── FilterTabs (전체/진행중/종료됨)
│   ├── SearchBar
│   ├── EventCardGrid
│   │   └── EventCard[]
│   └── Pagination
├── EventDetailPage (상세)
│   ├── EventHeader (배너+제목+상태)
│   ├── EventInfo (좌측: 설명+조건)
│   │   └── Checklist (참여 조건)
│   ├── EventSidebar (우측: 보상+참여버튼)
│   ├── ParticipantList (참여자 테이블)
│   │   └── ParticipantRow[]
│   └── RelatedEvents
│       └── EventCard[]
└── Footer
```

### 3.2 컴포넌트 명세

| 컴포넌트 | Props | 설명 |
|----------|-------|------|
| `EventCard` | event, compact? | 배지, 이미지, 제목, 남은시간, 참여자수, 보상, 상태 |
| `FilterTabs` | activeTab, onTabChange, counts | 전체/진행중/종료됨 탭 + 각 탭 카운트 배지 |
| `SearchBar` | value, onSearch | 검색 입력 |
| `HeroBanner` | slides[] | 자동 슬라이드 배너 (Swiper.js 기반) |
| `Checklist` | conditions[], userProgress | 참여조건 체크리스트 |
| `ParticipantList` | participants[], eventId | 참여자 테이블 + 필터 + 페이지네이션 |
| `ParticipantRow` | participant | 닉네임, 참여일, 상태, 진행도 바 |
| `Pagination` | currentPage, totalPages, onPageChange | 페이지 네비게이션 |
| `EventSidebar` | event, onParticipate | 보상 정보 + 참여/완료 버튼 |
| `RelatedEvents` | currentEventId, events[] | 관련 이벤트 카드 그리드 |

---

## 4. 데이터 구조 (JSON 스키마)

### 4.1 events.json

```jsonc
{
  "$schema": "events-schema-v1",
  "events": [
    {
      "id": "evt_001",
      "slug": "april-post-event",
      "title": "4월 커뮤니티 게시글 이벤트",
      "description": "커뮤니티에 유익한 글을 작성하고 포인트를 받으세요!",
      "longDescription": "Markdown 형식의 상세 설명...",
      "bannerImage": "/images/events/evt_001_banner.webp",
      "thumbnailImage": "/images/events/evt_001_thumb.webp",
      "badge": {
        "label": "COMMUNITY",
        "color": "#FF4444"
      },
      "status": "active",  // "upcoming" | "active" | "ended"
      "startDate": "2026-04-01T00:00:00+09:00",
      "endDate": "2026-04-30T23:59:59+09:00",
      "reward": {
        "type": "points",
        "amount": 50,
        "unit": "P",
        "description": "포인트 50P"
      },
      "conditions": [
        {
          "id": "cond_001",
          "type": "follow",
          "platform": "telegram",
          "label": "텔레그램 채널 팔로우",
          "url": "https://t.me/fireantcrypto",
          "autoVerify": false
        },
        {
          "id": "cond_002",
          "type": "retweet",
          "platform": "twitter",
          "label": "트위터 리트윗",
          "url": "https://twitter.com/fireantcrypto/status/xxx",
          "autoVerify": false
        },
        {
          "id": "cond_003",
          "type": "join",
          "platform": "discord",
          "label": "디스코드 가입",
          "url": "https://discord.gg/fireant",
          "autoVerify": false
        },
        {
          "id": "cond_004",
          "type": "custom",
          "platform": "community",
          "label": "커뮤니티 게시글 작성 (1편 이상)",
          "url": "https://fireantcrypto.com/board",
          "autoVerify": false
        }
      ],
      "participantCount": 142,
      "maxParticipants": null,
      "tags": ["community", "posting", "monthly"],
      "category": "community",
      "createdAt": "2026-03-25T10:00:00+09:00",
      "updatedAt": "2026-04-10T18:00:00+09:00"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 12,
    "totalItems": 47,
    "totalPages": 4
  }
}
```

### 4.2 participants.json (이벤트별)

```jsonc
{
  "$schema": "participants-schema-v1",
  "eventId": "evt_001",
  "participants": [
    {
      "id": "p_001",
      "userId": "user_042",
      "nickname": "fire_ant_01",
      "walletAddress": null,
      "joinedAt": "2026-04-08T14:30:00+09:00",
      "status": "completed",  // "in_progress" | "completed" | "disqualified"
      "progress": {
        "totalConditions": 4,
        "completedConditions": 4,
        "conditions": [
          { "conditionId": "cond_001", "completed": true, "verifiedAt": "2026-04-08T14:31:00+09:00" },
          { "conditionId": "cond_002", "completed": true, "verifiedAt": "2026-04-08T14:35:00+09:00" },
          { "conditionId": "cond_003", "completed": true, "verifiedAt": "2026-04-08T14:40:00+09:00" },
          { "conditionId": "cond_004", "completed": true, "verifiedAt": "2026-04-09T10:00:00+09:00" }
        ]
      },
      "rewardClaimed": false
    },
    {
      "id": "p_002",
      "userId": "user_089",
      "nickname": "crypto_kim",
      "walletAddress": null,
      "joinedAt": "2026-04-08T16:00:00+09:00",
      "status": "in_progress",
      "progress": {
        "totalConditions": 4,
        "completedConditions": 2,
        "conditions": [
          { "conditionId": "cond_001", "completed": true, "verifiedAt": "2026-04-08T16:01:00+09:00" },
          { "conditionId": "cond_002", "completed": true, "verifiedAt": "2026-04-08T16:05:00+09:00" },
          { "conditionId": "cond_003", "completed": false, "verifiedAt": null },
          { "conditionId": "cond_004", "completed": false, "verifiedAt": null }
        ]
      },
      "rewardClaimed": false
    }
  ],
  "summary": {
    "totalParticipants": 142,
    "completed": 67,
    "inProgress": 75,
    "rewardClaimed": 0
  },
  "pagination": {
    "page": 1,
    "pageSize": 50,
    "totalItems": 142,
    "totalPages": 3
  }
}
```

---

## 5. 기술 스택 제안

### 5.1 옵션 비교

| 항목 | A. 정적 사이트 확장 (현재) | B. Astro + 리액트 아일랜드 | C. Next.js (SSG/ISR) |
|------|---------------------------|--------------------------|---------------------|
| **호스팅** | GitHub Pages (무료) | GitHub Pages / Vercel | Vercel / Cloudflare Pages |
| **빌드** | 매번 전체 리빌드 | 부분 하이드레이션 | ISR로 변경분만 갱신 |
| **동적 데이터** | JS fetch + JSON | JS fetch + JSON | API Routes + DB 직접 |
| **참여자 데이터** | 외부 API 호출 | 외부 API 호출 | 내장 API + DB |
| **검색** | 클라이언트 사이드 | 클라이언트 사이드 | 서버 사이드 가능 |
| **SEO** | 좋음 | 매우 좋음 | 매우 좋음 |
| **복잡도** | 낮음 | 중간 | 높음 |
| **마이그레이션 공수** | 없음 | 1-2일 | 3-5일 |
| **확장성** | 제한적 | 좋음 | 매우 좋음 |

### 5.2 추천: 옵션 B (Astro + 리액트 아일랜드)

**이유:**
- 정적 호스팅(GitHub Pages) 유지 가능 → 비용 없음
- 마크다운/MDX로 이벤트 페이지 관리 가능
- 필요한 부분만 리액트로 하이드레이션 → 빠른 로딩
- 참여자 데이터는 클라이언트에서 fetch → SQLite API 경유
- 나중에 Next.js로 전환 필요시 리액트 컴포넌트 재사용 가능

**대안 (Phase 3 이후):** 참여자 데이터가 많아지고 실시간 업데이트가 필요하면 Next.js + Vercel로 전환. Phase 1-2는 Astro로 충분.

### 5.3 데이터 API 아키텍처

```
[정적 사이트]  ──fetch──>  [Cloudflare Worker / Vercel Serverless]
                                  │
                                  ├── /api/events          (이벤트 목록)
                                  ├── /api/events/:id      (이벤트 상세)
                                  ├── /api/events/:id/participants (참여자)
                                  └── /api/participate     (참여 등록)
                                        │
                                        ▼
                                  [SQLite DB / Turso]
```

- 기존 `bots/referral-bot/` SQLite 스키마 확장
- Serverless 함수로 API 제공 (Cloudflare Workers 무료 플랜 충분)
- 참여자 수가 많아지면 Turso (SQLite 호스팅) 고려

---

## 6. 구현 우선순위

### Phase 1: MVP (1주, ~40시간)

**목표: 이벤트 카드 그리드 + 상세 페이지 + 상태 필터**

| 작업 | 시간 | 상세 |
|------|------|------|
| Astro 프로젝트 셋업 | 2h | 기존 사이트 구조 마이그레이션 |
| 이벤트 데이터 JSON 설계 | 2h | 위 스키마 기반 |
| EventCard 컴포넌트 | 4h | 배지, 이미지, 제목, 상태, 카운트다운 |
| FilterTabs 컴포넌트 | 2h | 전체/진행중/종료됨 |
| SearchBar 컴포넌트 | 2h | 클라이언트 사이드 검색 |
| Pagination 컴포넌트 | 2h | 페이지네이션 |
| 이벤트 리스트 페이지 | 4h | 히어로 배너 + 필터 + 그리드 |
| 이벤트 상세 페이지 | 6h | 정보 + 체크리스트 + 사이드바 |
| HeroBanner 슬라이더 | 3h | Swiper.js 연동 |
| 스타일링 (다크 테마) | 4h | 불개미 브랜딩 적용 |
| 반응형 (모바일) | 4h | 모바일 카드 1-2열 대응 |
| 기존 이벤트 데이터 입력 | 3h | 과거 이벤트 아카이빙 |
| 테스트 + 버그픽스 | 2h | 크로스 브라우저 |

**코드 예시 — EventCard (Astro + React)**

```astro
---
// src/pages/events/index.astro
import EventCard from '../components/EventCard.tsx';
import FilterTabs from '../components/FilterTabs.tsx';

const allEvents = await fetchEvents(); // JSON에서 로드
const activeEvents = allEvents.filter(e => e.status === 'active');
const endedEvents = allEvents.filter(e => e.status === 'ended');
---

<FilterTabs client:load counts={{
  all: allEvents.length,
  active: activeEvents.length,
  ended: endedEvents.length
}} />

{activeEvents.map(event => (
  <EventCard client:load event={event} />
))}
```

```tsx
// src/components/EventCard.tsx
import { useState, useEffect } from 'react';

interface EventCardProps {
  event: {
    id: string;
    title: string;
    thumbnailImage: string;
    status: string;
    endDate: string;
    participantCount: number;
    reward: { amount: number; unit: string };
    badge: { label: string; color: string };
  };
}

export default function EventCard({ event }: EventCardProps) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    const update = () => {
      const diff = new Date(event.endDate).getTime() - Date.now();
      if (diff <= 0) { setTimeLeft('종료됨'); return; }
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      setTimeLeft(`${days}일 ${hours}시간 남음`);
    };
    update();
    const timer = setInterval(update, 60000);
    return () => clearInterval(timer);
  }, [event.endDate]);

  return (
    <a href={`/events/${event.id}`} className="event-card">
      <div className="badge" style={{ background: event.badge.color }}>
        {event.status === 'active' ? '🔴 LIVE' : '종료됨'}
      </div>
      <img src={event.thumbnailImage} alt={event.title} loading="lazy" />
      <h3>{event.title}</h3>
      <div className="meta">
        <span>⏰ {timeLeft}</span>
        <span>👥 {event.participantCount}명</span>
        <span>💰 {event.reward.amount}{event.reward.unit}</span>
      </div>
    </a>
  );
}
```

**코드 예시 — FilterTabs**

```tsx
// src/components/FilterTabs.tsx
import { useState } from 'react';

interface FilterTabsProps {
  counts: { all: number; active: number; ended: number };
  onFilterChange?: (tab: string) => void;
}

export default function FilterTabs({ counts }: FilterTabsProps) {
  const [active, setActive] = useState('all');
  
  const tabs = [
    { key: 'all', label: '전체', count: counts.all },
    { key: 'active', label: '진행중', count: counts.active },
    { key: 'ended', label: '종료됨', count: counts.ended },
  ];

  return (
    <div className="filter-tabs">
      {tabs.map(tab => (
        <button
          key={tab.key}
          className={`tab ${active === tab.key ? 'active' : ''}`}
          onClick={() => setActive(tab.key)}
        >
          {tab.label} <span className="count">{tab.count}</span>
        </button>
      ))}
    </div>
  );
}
```

---

### Phase 2: 참여자 데이터 연동 + 아카이빙 (2주, ~60시간)

| 작업 | 시간 | 상세 |
|------|------|------|
| API 서버 구축 (Cloudflare Workers) | 8h | DB 연동 API |
| DB 스키마 설계 | 4h | events + participants + conditions 테이블 |
| 기존 데이터 마이그레이션 | 6h | 구글폼/텔레그램봇 데이터 → DB |
| ParticipantList 컴포넌트 | 8h | 테이블 + 필터 + 페이지네이션 |
| Checklist 컴포넌트 (동적) | 6h | 조건별 완료 상태 표시 |
| 참여 등록 플로우 | 8h | 폼 제출 → DB 저장 |
| 관리자 페이지 (이벤트 CRUD) | 10h | 이벤트 생성/수정/종료 처리 |
| 참여자 관리 페이지 | 6h | 수동 검증, 상태 변경 |
| 검색 기능 고도화 | 4h | 태그/카테고리/기간 필터 |
**코드 예시 — API (Cloudflare Worker)**

```typescript
// api/index.ts — Cloudflare Worker
interface Env {
  DB: D1Database; // Cloudflare D1 (SQLite)
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': 'https://fireantcrypto.com',
      'Content-Type': 'application/json',
    };

    // GET /api/events
    if (url.pathname === '/api/events' && request.method === 'GET') {
      const status = url.searchParams.get('status') || 'all';
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = 12;
      const offset = (page - 1) * limit;

      const where = status !== 'all' ? `WHERE status = '${status}'` : '';
      const { results } = await env.DB.prepare(
        `SELECT * FROM events ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`
      ).bind(limit, offset).all();

      return new Response(JSON.stringify({ events: results }), { headers: corsHeaders });
    }

    // GET /api/events/:id/participants
    if (url.pathname.match(/^\/api\/events\/[^/]+\/participants$/)) {
      const eventId = url.pathname.split('/')[3];
      const { results } = await env.DB.prepare(
        `SELECT p.*, u.nickname 
         FROM participants p 
         JOIN users u ON p.user_id = u.id 
         WHERE p.event_id = ? 
         ORDER BY p.joined_at DESC`
      ).bind(eventId).all();

      return new Response(JSON.stringify({ participants: results }), { headers: corsHeaders });
    }

    // POST /api/participate
    if (url.pathname === '/api/participate' && request.method === 'POST') {
      const body = await request.json() as {
        eventId: string;
        userId: string;
        conditions: Record<string, boolean>;
      };

      await env.DB.prepare(
        `INSERT INTO participants (id, event_id, user_id, status, progress, joined_at)
         VALUES (?, ?, ?, 'in_progress', ?, datetime('now'))`
      ).bind(
        crypto.randomUUID(),
        body.eventId,
        body.userId,
        JSON.stringify(body.conditions)
      ).run();

      return new Response(JSON.stringify({ success: true }), { headers: corsHeaders });
    }

    return new Response('Not found', { status: 404 });
  }
};
```

**코드 예시 — DB 스키마**

```sql
-- migrations/001_initial.sql

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
  status TEXT DEFAULT 'upcoming' CHECK(status IN ('upcoming','active','ended')),
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  reward_type TEXT,
  reward_amount INTEGER DEFAULT 0,
  reward_unit TEXT DEFAULT 'P',
  reward_description TEXT,
  max_participants INTEGER,
  category TEXT,
  tags TEXT, -- JSON array
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

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

CREATE TABLE IF NOT EXISTS participants (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  nickname TEXT NOT NULL,
  wallet_address TEXT,
  status TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress','completed','disqualified')),
  progress TEXT DEFAULT '{}', -- JSON
  reward_claimed INTEGER DEFAULT 0,
  joined_at TEXT DEFAULT (datetime('now')),
  completed_at TEXT,
  UNIQUE(event_id, user_id)
);

CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_participants_event ON participants(event_id);
CREATE INDEX idx_participants_user ON participants(user_id);
```

---

### Phase 3: 지갑 연동 + 자동 참여 확인 (3주, ~80시간)

| 작업 | 시간 | 상세 |
|------|------|------|
| 지갑 연동 (MetaMask/WalletConnect) | 12h | Web3 로그인 |
| 온체인 검증 로직 | 12h | 트랜잭션/홀딩 확인 |
| 소셜 자동 검증 | 12h | Twitter API / Telegram Bot 연동 |
| 실시간 참여 상태 업데이트 | 8h | WebSocket / Polling |
| 리워드 자동 분배 | 8h | 스마트 컨트랙트 또는 수동 일괄 처리 |
| 유저 대시보드 | 10h | 내 참여 이력, 포인트, 보상 현황 |
| 이메일/알림 시스템 | 6h | 이벤트 시작/마감 알림 |
| 보안 강화 | 6h | Rate limiting, Sybil 방지 |
| 성능 최적화 | 6h | 캐싱, CDN, lazy loading |

---

## 7. 예상 공수 요약

| Phase | 기간 | 시간 | 담당 | 산출물 |
|-------|------|------|------|--------|
| **Phase 1 (MVP)** | 1주 | ~40h | 프론트 1명 | 이벤트 리스트/상세 페이지, 정적 데이터 |
| **Phase 2 (참여자 연동)** | 2주 | ~60h | 풀스택 1명 | API 서버, DB, 관리자 페이지 |
| **Phase 3 (지갑/자동화)** | 3주 | ~80h | 풀스택 1명 + Web3 1명 | 지갑 연동, 자동 검증, 리워드 |
| **총계** | 6주 | ~180h | | 프로덕션 이벤트 플랫폼 |

### Phase 1만 먼저 (추천 시작점)

- **1주일 내** 이벤트 섹션 런칭 가능
- 정적 JSON으로 이벤트 관리 → 나중에 DB로 전환
- 과거 이벤트 아카이빙 즉시 가능
- 참여자 리스트는 Phase 2에서 추가

---

## 부록: 디자인 가이드라인

### 색상 팔레트

```css
:root {
  /* 기존 불개미 브랜딩 */
  --fireant-red: #FF4444;
  --fireant-red-dark: #CC3333;
  
  /* 다크 테마 */
  --bg-primary: #0a0a0f;
  --bg-secondary: #141420;
  --bg-card: #1a1a2e;
  --bg-card-hover: #222240;
  
  /* 텍스트 */
  --text-primary: #ffffff;
  --text-secondary: #a0a0b0;
  --text-muted: #666680;
  
  /* 상태 */
  --status-active: #00FF88;
  --status-ended: #888888;
  --status-upcoming: #FFD700;
  
  /* 보상 */
  --reward-gold: #FFD700;
  --reward-green: #00FF88;
}
```

### 카드 CSS 예시

```css
.event-card {
  background: var(--bg-card);
  border-radius: 16px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.event-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(255, 68, 68, 0.15);
  border-color: rgba(255, 68, 68, 0.3);
}

.event-card .badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  z-index: 1;
}

.event-card .meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}

.event-card h3 {
  color: var(--text-primary);
  font-size: 16px;
  padding: 0 16px;
  margin: 12px 0 8px;
  line-height: 1.4;
}

/* 그리드 */
.events-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

@media (max-width: 1024px) {
  .events-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .events-grid { grid-template-columns: 1fr; }
}
```

---

*이 문서는 구현 계획서이며, 실제 개발 시작 전 해병님과 리뷰 후 확정한다.*
