# 이미지 생성 및 전송 시스템 오류 정밀 분석 보고서

**분석 기간:** 2026-04-13 01:01 ~ 02:01 (최근 60분)
**수집 로그:** gateway.log (23,297라인), gateway.err.log (215라인)
**분석 대상 도구:** image_generate (6건), message/send_image (12건)

---

## 1. image_generate 도구 실패 분석 (총 6건)

### 1-A. OpenAI 빌링 한도 초과 (4건)
| 시간 | 프롬프트 요약 | 결과 |
|------|-------------|------|
| 01:15:45 | 개미 공장 인포그래픽 | ALL FAIL (3개 모델 전원 실패) |
| 01:53:43 | FireAnt 공식 배너 | ALL FAIL |
| 01:54:07 | 크립토 리포트 배너 | ALL FAIL |
| 01:56:18 | 초고품질 금융 리포트 배너 | ALL FAIL |

**실패 모델별 원인:**
- `google/gemini-3.1-flash-image-preview`: "This operation was aborted" (타임아웃/취소)
- `openai/gpt-image-1.5`: "Billing hard limit has been reached" (`billing_hard_limit_reached`)
- `openai/gpt-image-1`: "Billing hard limit has been reached" (`billing_hard_limit_reached`)

**원인:** OpenAI 이미지 생성 API의 사용 한도(billing hard limit)에 도달하여 모든 요청이 400 에러로 거부됨. Gemini 대안도 타임아웃으로 실패하여 3중 폴백이 모두 실패.

**근거:** gateway.err.log의 `[tools] image_generate failed` 항목. HTTP 400 + `billing_hard_limit_reached` 코드 확인.

### 1-B. 참조 이미지 파일 누락 (2건)
| 시간 | 누락 파일 |
|------|----------|
| 01:32:08 | `/assets/img/logo/fireant_logo_main.png` |
| 01:32:36 | `/workspace/current_logo.png` |

**원인:** image_generate의 `image` 파라미터로 전달한 참조 로고 파일이 존재하지 않음. `fireant_logo_main.png`는 실제로 디스크에 없으며, `current_logo.png`는 존재하나 하네스 샌드박스 내 경로 매핑 불일치 가능.

**근거:** 파일 존재 여부 검증 결과 `fireant_logo_main.png` → MISSING, `current_logo.png` → EXISTS (하지만 컨텍스트 내에서 인식 실패).

---

## 2. message/send_image 도구 실패 분석 (총 12건)

### 2-A. 로컬 미디어 파일 미존재 (7건)
| 시간 | 누락 파일 | 도구 |
|------|----------|------|
| 01:07:54 | report_banner_final.png | image |
| 01:07:57 | report_banner_final.png | image |
| 01:08:19 | report_banner_final.png | image |
| 01:17:08 | fireant_report_banner.png | image |
| 01:48:51 | fireant_official_banner.png | message |
| 01:49:21 | REALLY_FINAL_BANNER.png | message |
| 01:50:41 | REALLY_FINAL_BANNER.png | exec_command |

**원인:** image_generate가 실패한 상태에서 후속 message/send_image 도구가 해당 산출물 경로를 참조. 선행 작업(image_generate)이 실패했으므로 파일이 생성되지 않았고, 후속 전송도 연쇄 실패.

**근거:** image_generate 실패 시각(01:15, 01:32, 01:53~) 이후 message 실패 시각(01:48~01:50)이 일치. report_banner_final.png는 01:08에 생성되었으나 이후 디렉토리에서 사라짐 (하네스 작업공간 정리에 의한 삭제 추정).

### 2-B. 잘못된 텔레그램 수신자 (3건)
| 시간 | 오류 |
|------|------|
| 01:23:56 | @heartbeat → chat not found (400) |
| 01:24:21 | @heartbeat → chat not found (400) |
| 01:24:39 | @heartbeat → chat not found (400) |

**원인:** `@heartbeat`는 텔레그램 사용자명이 아닌 시스템 내부 식별자. 에이전트가 하드코딩된 대상을 사용하여 텔레그램 getChat API에서 400 Bad Request 발생.

**근거:** error 메시지 "Telegram recipient @heartbeat could not be resolved to a numeric chat ID"

### 2-C. 필수 파라미터 누락 (1건)
| 시간 | 오류 |
|------|------|
| 01:24:08 | "message required" |

**원인:** message 도구에 `action=send`와 `caption`만 전달하고 `message` 본문을 누락.

### 2-D. 샌드박스 경로 접근 제한 (1건)
| 시간 | 오류 |
|------|------|
| 01:52:41 | LocalMediaAccessError: 허용되지 않은 경로 |

**원인:** 에이전트가 `/Users/fireant/Desktop/fi...` 경로의 파일을 전송하려 시도했으나, 샌드박스 보안 정책상 허용된 디렉토리(`/workspace` 하위) 외부의 파일 접근이 차단됨.

---

## 3. LLM Rate Limit 연쇄 영향

최근 1시간 동안 zai/glm-5.1 프로바이더에서 **다수의 429 에러** 발생:
- "Weekly/Monthly Limit Exhausted" (리셋 예정: 2026-04-13 14:28:14)
- "API rate limit reached"

이로 인해 에이전트 응답이 지연되고, 폴백 모델(gemini-3-flash-preview)로 전환되었으나 cron 작업 타임아웃(166,683ms) 발생.

---

## 요약: 원인 / 근거 / 재발방지

### ▶ image_generate 실패

| 항목 | 내용 |
|------|------|
| **원인** | (1) OpenAI 이미지 생성 API 빌링 한도(billing_hard_limit_reached) 초과로 gpt-image-1, gpt-image-1.5 모두 400 에러. (2) Gemini Flash Image Preview 모델 타임아웃/abort. (3) 참조 이미지 파일 경로 오류. |
| **근거** | gateway.err.log에 `[tools] image_generate failed: All image generation models failed (3)` 기록. HTTP 400 + `billing_hard_limit_reached` 코드. 총 4회 반복. |
| **재발방지** | ① OpenAI 계정의 billing hard limit 상향 또는 사용량 모니터링 알림 설정. ② 이미지 생성 폴백 체인에 로컬 Pillow 스크립트 생성(현재 구현됨)을 최우선으로 배치. ③ 빌링 한도 초과 시 자동으로 Pillow 경로로 전환하는 라우팅 로직 추가. ④ 참조 이미지 경로를 사용 전 반드시 `stat`/`exists` 검증. |

### ▶ message/send_image 실패

| 항목 | 내용 |
|------|------|
| **원인** | (1) 선행 image_generate 실패로 산출물 파일이 생성되지 않아 연쇄 실패. (2) 텔레그램 수신자 `@heartbeat`가 유효하지 않은 사용자명. (3) 샌드박스 허용 경로 외부 파일 접근 시도. |
| **근거** | `[tools] message failed: Local media file not found` (7건). `[tools] message failed: Telegram recipient @heartbeat could not be resolved` (3건). `LocalMediaAccessError` (1건). |
| **재발방지** | ① send_image 실행 전 파일 존재 여부 사전 검증 로직 추가. ② 에이전트 프롬프트에 하드코딩 금지 및 동적 chat ID 조회 지시 추가. ③ 작업 체인에서 선행 단계 실패 시 후속 전송 단계를 자동 스킵. ④ 샌드박스 내에서만 작업하도록 경로 화이트리스트 명시. |
