# Ollama 실행 상태 및 bge-m3 모델 설치 확인 결과 보고서

## 1. Ollama 실행 여부 + bge-m3 모델 설치 확인

### 프로세스 상태 (pgrep -l ollama)
```
1093 ollama
3109 ollama
```
✅ Ollama 정상 실행 중 (PID 1093, 3109)

### bge-m3 모델 (ollama list)
```
bge-m3:latest    790764642607    1.2 GB    6 weeks ago
```
✅ bge-m3:latest 모델 설치됨 (1.2 GB, 6주 전)

### /api/tags 엔드포인트
```
bge-m3:latest
```
✅ localhost:11434 정상 응답

---

## 2. Gemini 모델 설정 (openclaw.json)
```
Current fallbacks: []
subagents: {'maxConcurrent': 5, 'model': {'primary': 'google/gemini-3-pro-preview'}}
imageModel: {'primary': 'google/gemini-3.1-flash-image-preview'}
imageGenerationModel: {'primary': 'google/gemini-3.1-flash-image-preview', 'fallbacks': ['openai/gpt-image-1.5', 'openai/gpt-image-1']}
```
⚠️ preview 버전 사용 중. GA 정식 버전으로의 전환 시점 확인 필요.

---

## 3. 크론 시간 분산 상태 + 동시 실행 카운트
```
✅ 00:00 — 1개: memory-db-backup
✅ 01:00 — 1개: codex-openai-auto-reauth-d5
🔴 03:00 — 2개: self-learning-daily-analysis, Memory Dreaming Promotion
🔴 09:00 — 5개: codex-token-refresh, self-learning-weekly-report, Google OAuth 자동갱신, bridge34-calendar-sync, harness-daily-healthcheck
✅ 14:00 — 1개: daily-cb-premium-ask
✅ 14:55 — 1개: daily-chalk-chammo-prep
✅ 15:00 — 1개: daily-chalk-main-event
✅ 16:30 — 1개: dashboard-daily-report-refresh-17
✅ 17:00 — 1개: daily-naver-blog-post
```
🔴 09:00에 5개 동시 실행 병목 — 시간 분산 권장
🔴 03:00에 2개 동시 실행

---

## 4. auth-state.json cooldown 상태
```
zai:fallback: 정상
zai:default: cooldown 232분 남음
google:default: 정상
```
⚠️ zai:default cooldown 약 232분 남음

---

## 최종 요약 (3줄)

✅ Ollama 정상 실행 중, bge-m3 모델 설치됨. cron 09:00에 5개 동시 실행 병목 존재.

요약:
1. Ollama PID 1093/3109로 실행 중, bge-m3:latest(1.2 GB) 모델 설치됨. /api/tags 정상 응답.
2. 4가지 확인 항목 모두 정상 실행 완료. 파일 수정 없음.
3. 09:00 크론 5개 동시 실행 병목, zai:default cooldown 232분 남음, Gemini preview 버전 사용 중.

변경 파일: report-ollama-status.md (본 보고서)

실행한 테스트:
- pgrep -l ollama → PID 1093, 3109
- ollama list | grep bge → bge-m3:latest 확인
- curl /api/tags → bge-m3:latest 정상 응답
- openclaw.json 파싱 → Gemini preview 설정 확인
- 크론 스케줄 분산 분석 → 09:00 병목 5개 🔴
- auth-state.json cooldown → zai:default 232분 남음

경고:
- 09:00 크론 병목: 5개 잡 동시 실행 → 시간 분산 권장
- zai:default cooldown 232분 남음
- Gemini GA 버전 미적용: preview 사용 중
