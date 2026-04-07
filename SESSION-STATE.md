## Problem-Solving State
- **Goal**: 일일시황 데이터 수집 및 이미지 생성, 보고서 작성
- **Blocker Class**: technical (브라우저 도구 타임아웃/차단)
- **Path Map**:
  1. browser 도구로 iamstarchild, sosovalue 파싱 (실패)
  2. python requests 스크립트로 직접 크롤링 (차단됨)
  3. web_search로 최신 뉴스 기사에서 수치 추출 (성공)
  4. 코인베이스 프리미엄은 히스토리 파일 폴백 사용 (성공)
- **Active Paths**:
  - [x] web_search로 BTC, ETH ETF 유출입 확인
  - [x] web_search로 미결제약정 24h 확인
  - [x] gen_daily_report_html.py로 이미지 생성 완료
- **Switch Trigger**: N/A
- **Next Fallback**: N/A

- **Tech Lesson (2026-04-08)**: OAuth 인증 시 run_local_server 금지 (OOB 방식 사용). 백그라운드 프로세스 대기 시 턴 종료 금지 및 30초 초과 시 중간보고.
- **Delegation Reminder (2026-04-08)**: 조사/브리핑/글쓰기/번역/문서 초안은 참모(chammo), 코드/봇/HTML/CSS/대시보드/배포/시스템 점검은 공병(ops) 우선 위임. 봇/게시판 작동점검도 공병 대상. 직접 실행은 도구 2회 이하 즉답/긴급/실시간 작업만.
