# 기술 교훈 및 도구 설정
# 검색 키워드: 기술 교훈, 버그, reasoning 누출, API 키, Fireflies,
# 크리덴셜, OpenClaw 설정, 텔레그램 웹뷰, X 수집 제한, 브라우저,
# contextPruning, 서브에이전트, 에러, 장애, 설정, config

## 운영 원칙
- 모든 날짜/요일/시간은 한국시간(KST) 기준으로 표기
- **텔레그램 링크(t.me/*) 확인 규칙**: 반드시 `browser` 툴로 직접 열어서 확인. `web_fetch`로 시도하거나 해병님에게 내용 요청 절대 금지. 브라우저 타임아웃 시 gateway restart 후 재시도.

## Google 계정 우선순위 (2026-03-14 확정)
- **1순위**: `fireant@bridge34.com` — 캘린더, 드라이브, 시트, 슬라이드, 독스, Forms 전부
- **2순위**: `josoyjjk@gmail.com` — 1순위 실패 시 fallback
- OAuth 토큰: `secrets/google-token.json` (bridge34.com 계정 기준)

## 알려진 이슈
- reasoning/thinking 출력이 텔레그램 메시지로 노출되는 버그 (2026-02-24~25):
  - 원인: openclaw.json에 무효 키(`streaming`, `ownerDisplay`) 사용 → 설정 미적용
  - 해결: (1) 무효 키 제거 (2) 올바른 키 `streamMode: "off"` 적용 (3) AGENTS.md에 `/reasoning off` 매 세션 실행 추가
  - 참고: `reasoning: false`는 config-level 키가 아님 (agents.defaults에도 models에도 Unrecognized). 세션 명령 `/reasoning off`만 유효.
  - 올바른 텔레그램 설정 키: `botToken`, `dmPolicy`, `allowFrom`, `groupPolicy`, `streamMode` (NOT `streaming`)
  - 관련 이슈: GitHub openclaw/openclaw #24626, #24376
- openclaw.json 무효 키 문제 (2026-02-25 수정):
  - `commands.ownerDisplay`, `channels.telegram.streaming`, `gateway.errorHandling`, `gateway.logging` 모두 Unrecognized
  - config reload가 계속 실패하여 설정 변경이 적용되지 않음 → 답변 끊김/failover 실패의 근본 원인
  - 해결: 무효 키 전부 제거
- 텔레그램 공개 웹뷰(t.me/s)는 일부 과거 글만 부분 수집 가능(파라미터 before 활용)
- X는 비로그인/보안정책으로 자동 수집 제한될 수 있음

## 컨텍스트 최적화 (2026-02-24 적용)
- Plan B: contextPruning cache-ttl 60분, keepLastAssistants 6, minPrunableToolChars 2000
- Plan C: 도구 호출 3회+ 예상 시 서브에이전트 위임
- Plan A: MEMORY.md 분리 완료 (style/projects/people/tech)

## 내부 tool 오류 알림 텔레그램 노출 (2026-03-13)
- 증상: Edit 도구 실패 시 "⚠️ 📝 Edit: ... failed" 메시지가 텔레그램으로 전송됨
- 원인: OpenClaw platform이 tool 오류를 채널에 push하는 것으로 보임 (platform 버그)
- 상태: 미해결 (OpenClaw upstream 이슈)
- 대응: 중요 편집은 python 스크립트로 처리해 Edit 도구 실패 최소화

## 에이전트 모델 설정 (2026-04-08 23:37 KST 확정 — 실 테스트 검증)
- 딸수 (main): `anthropic/claude-sonnet-4-6` (fallback: `openai-codex/gpt-5.4`)
- 참모 (chammo): `google/gemini-3-pro-preview`
- 공병 (ops): `openai-codex/gpt-5.4`
- 작전장교 (inspector): `anthropic/claude-opus-4-6`
- 실제 서브에이전트 spawn 테스트로 검증 완료, 게이트웨이 재시작 적용

## Google 이미지 생성 키 교체 시 주의사항 (2026-03-30)
- auth-profiles.json 키 교체 후 게이트웨이 SIGUSR1 재시작으로는 런타임 캐시 미갱신
- image_generate 툴이 구 키를 계속 사용 → "API key expired" 반복 오류
- **해결**: 키 교체 후 반드시 cold restart (stop → start) 또는 API 직접 호출로 우회
- Google API 직접 호출: `gemini-3.1-flash-image-preview:generateContent` + `responseModalities: ["IMAGE","TEXT"]`

## OAuth 인증 및 백그라운드 프로세스 (2026-04-08)
- **금지**: 에이전트 환경에서 OAuth 인증 시 `run_local_server` 사용을 절대 금지합니다 (콜백 서버 유지 중 세션 끊김 발생).
- **권장**: 무조건 인증 코드를 직접 복사해서 입력받는 OOB(수동 코드 복사) 방식으로 고정합니다.
- **규칙**: 백그라운드 대기가 필요한 작업 시 턴(Turn)을 종료하고 대기하지 않습니다. 내 턴 안에서 `process poll`로 끝까지 대기하며, 30초가 넘어가면 반드시 `message` 툴로 중간보고를 발송합니다.
