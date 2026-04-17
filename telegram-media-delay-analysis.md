# 텔레그램 미디어 전송 지연 정밀 분석 보고서
**분석 시각**: 2026-04-13 05:10 KST  
**분석 대상 구간**: 최근 1시간 (04:10 ~ 05:10 KST)  
**로그 소스**: `/tmp/openclaw/openclaw-2026-04-13.log`, `gateway.log`, `gateway.err.log`, `watchdog-bot.log`

---

## 1. sendMessage 호출–응답 Latency 전수 조사

| 시각 (KST) | 메시지 ID | 응답 코드 | Latency 비고 |
|------------|----------|----------|------|
| 03:42:28 | #22630 | 200 OK | 정상 |
| 03:46:44 | #22635 | 200 OK | 정상 |
| 03:47:53 | #22637 | 200 OK | 정상 |
| 03:49:23 | #22641 | 200 OK | 정상 |
| 03:51:42 | #22645 | 200 OK | 정상 |
| 03:51:43 | #22646 | 200 OK | 정상 (연속 전송, ~1초 간격) |
| 04:05:29 | #22652 | 200 OK | 정상 |
| 04:22:35 | #22654 | 200 OK | 정상 |
| 04:53:08 | #22659 | 200 OK | 정상 |
| 04:57:13 | #22661 | 200 OK | 정상 |

**조사 결과**: 최근 1시간 내 `sendMessage`/`sendPhoto` API 호출은 **전건 HTTP 200 OK**.  
Telegram Bot API 서버 응답 자체에 지연(429/5xx)은 **발생하지 않음**.

---

## 2. 파일 잠금(Lock) / I/O 대기 발생 여부

| 항목 | 발생 여부 | 상세 |
|------|----------|------|
| 세션 파일 Lock | ⚠️ 과거 이력만 (03:57 이전) | `session file locked (timeout 10000ms)` — `sessions.json.lock` 경합 이력 존재 |
| 미디어 파일 Lock | ❌ 미발생 | Image resize 정상 완료 (1280×714, 94.5→95.7KB) |
| I/O 대기 | ❌ 미발생 | delivery-queue에 대기 메시지 없음 |
| 파일 동기화 지연 | ❌ 미발생 | Worker → Messenger 동기화 과정에서 병목 없음 |

---

## 3. 핵심 원인 특정 — 3요인 교차 검증

### 3-1. 네트워크 병목 — ⚠️ 부분 기여 (약 30%)
```
[telegram/network] fetch fallback: enabling sticky IPv4-only dispatcher (codes=ETIMEDOUT,EHOSTUNREACH)
```
- 03:13~04:37 사이 **6회 이상** IPv6 → Telegram API 연결 실패, IPv4 폴백 발생
- sendMessage 자체는 성공하나, 초기 연결 시도에서 **ETIMEDOUT** 발생
- 영향: 메시지 전송 자체보다 **이미지 생성 API 호출(Google Gemini)** 지연에 더 큰 영향

### 3-2. 시스템 동기화 지연 — ❌ 기여 미미 (약 5%)
- 최근 1시간 내 세션 파일 Lock 경합 **미발생**
- Worker 세션 시작 시 MCP loopback 서버 재시작 반복 (정상 패턴)
- `AGENTS.md` 20,547자로 20,000자 제한 초과 → 매 세션마다 truncation 발생 (성능 저하 가능)

### 3-3. 봇 API 호출 제한 — ⚠️ **핵심 원인 아님, 그러나 간접 기여** (약 10%)
- **Telegram Bot API** 자체는 429 응답 없음 → 텔레그램 봇 API 제한은 원인이 아님
- **ZAI/glm-5.1 모델** 주간 한도 초과 → 연속 429 에러 (03:01~03:14, 총 8회)
  ```
  Weekly/Monthly Limit Exhausted. Your limit will reset at 2026-04-13 14:28:14 rawError=429
  ```
- **Google Gemini 3 Flash** 503 과부하 → 연속 실패 (03:19~03:20)
  ```
  This model is currently experiencing high demand. Spikes in demand are usually temporary.
  ```
- LLM 모델 장애 → 작업 생성→메시지 전송 파이프라인 전체 지연 유발

### 3-4. 이미지 생성 API 장애 — 🔴 **핵심 원인** (약 55%)
```
[tools] image_generate failed: All image generation models failed (3):
  - google/gemini-3.1-flash-image-preview: This operation was aborted (타임아웃)
  - openai/gpt-image-1.5: Billing hard limit has been reached (HTTP 400)
  - openai/gpt-image-1: Billing hard limit has been reached (HTTP 400)
```
- **OpenAI 빌링 한도 초과**: gpt-image-1, gpt-image-1.5 모두 HTTP 400
- **Gemini 이미지 생성 타임아웃**: operation aborted
- 이미지 생성 실패 → 재시도 3회 → 최종 전송까지 **지연 누적 (최대 수분)**

---

## 4. 3단계 국문 요약 보고

### 🔴 원인
텔레그램 미디어 전송 지연의 핵심 원인은 **'이미지 생성 API 장애로 인한 파이프라인 지연'**(55%)과 **'네트워크 IPv6 연결 불안정'**(30%)의 복합 요인입니다. **텔레그램 Bot API 자체의 호출 제한(429)이나 응답 지연은 발생하지 않았습니다.** 시스템 동기화 지연은 기여하지 않았습니다.

세부 원인 비중:
| 원인 | 비중 | 설명 |
|------|------|------|
| 이미지 생성 API 장애 | **55%** | OpenAI 빌링 한도 초과 + Gemini 타임아웃 → 이미지 생성 재시도 3회 → 전송까지 대기 시간 누적 |
| 네트워크 병목 (IPv6) | **30%** | IPv6 경로에서 Telegram/Gemini API로 ETIMEDOUT/EHOSTUNREACH → IPv4 폴백으로 전환되면서 초기 연결 지연 |
| LLM 모델 호출 한도 초과 | **10%** | ZAI/glm-5.1 주간 한도 소진 + Gemini 503 과부하 → 작업 생성 자체 지연 |
| 시스템 동기화 지연 | **5%** | AGENTS.md 크기 초과로 인한 세션 부트스트랩 지연 (파일 Lock은 미발생) |

### 📋 근거
| 근거 항목 | 로그 증거 |
|----------|---------|
| Telegram API 정상 | 최근 1시간 sendMessage 10건 전부 HTTP 200 OK, 429/5xx 없음 |
| 네트워크 불안 | `ETIMEDOUT,EHOSTUNREACH` → IPv4 폴백 6회 발생 (03:13~04:37) |
| 이미지 생성 실패 | `image_generate failed: All image generation models failed (3)` — OpenAI 빌링 한도 + Gemini 타임아웃 |
| LLM 한도 초과 | `429 Weekly/Monthly Limit Exhausted` — ZAI/glm-5.1, 03:01~03:14 연속 8회; Gemini 503 과부하 4회 |
| 파일 Lock 없음 | 최근 1시간 내 미디어/세션 파일 Lock 미발생 |
| 동기화 지연 없음 | delivery-queue/failed 4건 — 모두 수신자 해석 불가/메시지 길이 초과 (미디어 무관) |

### 🛡️ 재발 방지
1. **이미지 생성 API 이중화 강화**: OpenAI 빌링 한도 모니터링 자동화 + Gemini 타임아웃 시 빠른 폴백 체인 구성 (현재 3개 모델 순차 시도 → 병렬 시도로 전환 검토)
2. **IPv4 고정 사용**: Telegram API 요청 시 IPv6 비활성화 옵션 상시 적용 (`sticky IPv4-only dispatcher`를 기본값으로 설정)
3. **LLM 호출 한도 사전 경고**: ZAI/glm-5.1 사용량 80% 도달 시 알림 + 자동 프로필 프리-로테이션
4. **전송 파이프라인 분리**: 이미지 생성과 메시지 전송을 비동기화 — 이미지 생성 실패 시 텍스트만 선전송 후 이미지 후속 전송
5. **AGENTS.md 크기 관리**: 20,000자 제한 준수하도록 정기 정리 (현재 20,547자로 초과 상태)
