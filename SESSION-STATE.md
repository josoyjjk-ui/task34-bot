## 시스템 업데이트 (2026-04-10)
- 모델 정책 확정: 딸수(zai/glm-5.1), 참모(google/gemini-3.1-flash-lite-preview), 공병(openai-codex/gpt-5.3-codex), 작전장교(anthropic/claude-opus-4-6)
- gemini-2.5-flash: TPM 한도 초과로 fallback에서 제거, 사용 금지
- 크론잡: payload.model 하드코딩 금지, agent defaults 따름
- 크론잡 배치: 콘텐츠→chammo, 인프라→ops, 모니터링→inspector, 나머지→main
- sessions_spawn: 모델 오버라이드 금지, agentId만 지정
- web_search: Gemini 기반 동작 중
- auth-profiles: ZAI/Anthropic/Google 키 등록 완료

## Problem-Solving State
- **Goal**: 일일시황 데이터 수집 및 이미지 생성, 보고서 작성
- **Blocker Class**: technical (브라우저 도구 타임아웃/차단)
- **Path Map**:
  1. browser 도구로 iamstarchild, sosovalue 파싱
  2. python requests 스크립트로 직접 크롤링
  3. web_search로 최신 기사/검색 결과 보강
  4. 로컬 템플릿 파일 기반 칠판형 이미지 재생성
  5. fallback 값으로 최소 보고 유지
- **Active Paths**:
  - [x] Sosovalue/Coinglass 값 재확인
  - [x] 칠판형 템플릿 재작성 필요사항 확정
- **Switch Trigger**: 같은 장벽 3회 → 경로 전환
- **Next Fallback**:
  - 기존 템플릿 파일 직접 수정
  - 부족 값은 미확보로 명시

- **Tech Lesson (2026-04-08)**: 사용자가 수정 방향을 주면 다음부터가 아니라 즉시 수행해야 함.
- **Top Priority Lesson (2026-04-08)**: 결과물 요청에서는 확인 질문 없이 바로 실행하고, 보고는 반드시 상황+원인+재발방지까지 세트로 한다.
- **Delegation Reminder (2026-04-08)**: 조사/브리핑/글쓰기/번역/문서 초안은 참모(chammo), 코드/봇/HTML/CSS/대시보드/배포/시스템 점검은 공병(ops) 우선 위임. 봇/게시판 작동점검도 공병 대상. 직접 실행은 도구 2회 이하 즉답/긴급/실시간 작업만.
- **Delegation Rule Update (2026-04-08)**: 리서치나 분석이 필요한 작업은 기본적으로 참모(chammo)에게 위임. 딸수는 실행 비서로서 누가 할지 판단하고 바로 굴린다.
