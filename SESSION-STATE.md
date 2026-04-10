## 최종 아키텍처 (2026-04-11)

### 에이전트 체제
- **유일 에이전트**: 딸수(main) 1명만 존재
- **삭제됨**: ops(공병), chammo(참모), inspector(작전장교) — 전부 없음

### 업무 처리 규칙 (절대)
- 해병님 지시 → 딸수 → **harness_execute** → 완료
- 간단한 질문만 직접 답변
- **sessions_spawn 사용 금지** (에이전트 없음)
- **harness_execute 우회 금지**
- **직접 도구 호출로 작업 처리 금지**

### 하네스 내부 별칭
- [공병] = 코딩 Worker (GLM-5.1, 파일생성/코드실행)
- [참모] = 리서치 Worker (Gemini Flash, 웹검색/분석)
- 작전장교 = 1st Reviewer (Codex 5.3)
- 정보장교 = 2nd Reviewer (Gemini Pro)
- Memory V3 = 자동 컨텍스트 (port 3457)

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
