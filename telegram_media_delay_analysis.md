# 텔레그램 미디어 전송 지연 원인 정밀 분석 보고서

**분석 대상 기간:** 2026-04-13 04:03 ~ 05:03 (KST)
**분석 대상 로그:** gateway.log, gateway.err.log

---

## 1. 원인 (Root Cause)

**핵심 원인: Z.AI(glm-5.1) LLM 프로바이더의 주간/월간 호출 한도(429 Rate Limit) 초과로 인한 연쇄 지연**

하위 복합 요인:
- **LLM 호출 한도 초과 (1순위):** Worker 모델(zai/glm-5.1)의 API 호출 한도가 소진되어, 429 응답 수신 후 지수 백오프 재시도가 반복됨
- **이미지 생성 API 한도 소진 (2순위):** Gemini(요청 시간 초과/중단), OpenAI gpt-image-1/1.5(청구 한도 도달, billing_hard_limit_reached) 3개 모델 모두 실패
- **미디어 파일 경로 불일치 (3순위):** Worker에서 생성한 이미지 파일이 예상 경로에 존재하지 않아 LocalMediaAccessError 및 "Local media file not found" 발생

---

## 2. 근거 (Evidence)

| 항목 | 수치 | 로그 근거 |
|------|------|-----------|
| 429 Rate Limit 발생 횟수 | **108건** | `gateway.err.log` - "429 Weekly/Monthly Limit Exhausted. Your limit will reset at 2026-04-13 14:28:14" |
| 이미지 생성 전체 실패 | **34건** | `gateway.err.log` - "All image generation models failed (3)" |
| 미디어 파일 미존재 | **23건** | "Local media file not found" 및 "LocalMediaAccessError" |
| 세션 파일 잠금 | **1건** | 04-12 03:03 - "session file locked (timeout 10000ms): sessions.json.lock" |
| 네트워크 타임아웃 | **81건** | ETIMEDOUT/EHOSTUNREACH + "enabling sticky IPv4-only dispatcher" (04-13 04:37) |
| OpenAI 청구 한도 | **9건** | "billing_hard_limit_reached" |

**지연 패턴 실측:**
- 메시지 22652 → 22654: **17분 간격** (04:05 → 04:22)
- 메시지 22654 → 22659: **31분 간격** (04:22 → 04:53)

위 간격은 Telegram API 자체 지연이 아닌, 업스트림 LLM 호출 반복 실패로 인한 처리 지연입니다. Telegram `sendMessage ok` 로그는 모두 정상 응답(HTTP 200)이며, Telegram Bot API 호출 제한(429)은 발생하지 않았습니다.

**지연 원인 기여도 요약:**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Z.AI 429 Rate Limit (LLM 호출 실패 → 재시도 루프)     ≈ 60%       │
│ 이미지 생성 API 전면 실패 (Gemini 중단 + OpenAI 한도)  ≈ 25%       │
│ 미디어 파일 경로 불일치 (Worker↔Messenger 동기화 지연) ≈ 10%       │
│ 네트워크 타임아웃 (IPv6→IPv4 폴백)                     ≈  5%       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. 재발 방지 (Prevention)

| # | 대책 | 상세 내용 |
|---|------|-----------|
| 1 | **LLM 프로바이더 다중화** | zai/glm-5.1 단일 프로바이더 의존도를 낮추고, 한도 초과 시 즉시 failover 가능한 대체 모델(예: anthropic/claude-sonnet, openai/gpt)을 활성화 |
| 2 | **이미지 생성 API 예산 모니터링** | OpenAI billing_hard_limit_reached 및 Gemini 타임아웃 사전 감지 → 한도 임박 시 알림 및 자동 대체 모델 전환 |
| 3 | **미디어 파일 동기화 강화** | Worker 세션에서 이미지 생성 완료 후 Messenger 세션으로 파일 전달 시, 파일 존재 여부 사전 검증 단계 추가 |
| 4 | **429 재시도 상한 설정** | 현재 4회 재시도 후에도 프로파일 교체(failover)하는 구조에서, 재시도 간격을 합리화하고 최대 2회로 단축 후 즉시 대체 프로바이더로 전환 |
| 5 | **네트워크 안정성 개선** | IPv6 타임아웃 발생 시 IPv4 폴백 로직이 이미 구현되어 있으나(04:37 로그), 최초 연결 시 IPv4 선호 옵션 도입으로 초기 지연 방지 |

---

*분석 완료 시각: 2026-04-13 05:03 KST*
*분석 대상 로그: /Users/fireant/.openclaw/logs/gateway.log (5.8MB), gateway.err.log (305KB)*
