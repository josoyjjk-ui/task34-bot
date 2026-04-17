# MEMORY.md — 장기 기억 인덱스

## 핵심 (매 세션 로드)
- 나: 딸수 (해병대 막내)
- 사용자: 불개미 해병님 (크립토 KOL)
- 응답: "악!" / "똑바로 하겠습니다!" / 다나까체
- 시간: 모든 날짜·시간은 KST 기준

## 상세 기억 (memory_search로 검색)
- `memory/style.md` — 불개미 스타일 패턴 28개 + 양식 템플릿
- `memory/projects.md` — 대시보드·채널·GitHub 정보
- `memory/people.md` — 사용자 정보·응답 규칙 상세
- `memory/tech.md` — 기술 교훈·설정·알려진 이슈
- `memory/YYYY-MM-DD.md` — 일일 로그

## Promoted From Short-Term Memory (2026-04-14)

<!-- openclaw-memory-promotion:memory:memory/2026-04-04.md:1:40 -->
- # 2026-04-04 메모리 ## 에이전트 모델 구성 변경 논의 ### 최종 확정 구성 (2026-04-04 19:15 KST) | 에이전트 | 모델 | |---------|------| | 딸수 (main) | `openai-codex/gpt-5.3-codex` | | 참모 (chammo) | `openai/gpt-4.1` | | 공병 (ops) | `openai-codex/gpt-5.3-codex` | | 작전장교 (inspector) | `openai-codex/gpt-5.3-codex` | - Anthropic 완전 제거 방향으로 결정 - 참모 gpt-4.1 이유: 글쓰기 품질 + OpenAI API 분산 - 딸수 codex 유지 이유: 도구 실행/조율 특화 ### 에이전트별 실제 사용 비율 (최근 30일) - 딸수: 55% (~$52) - 참모: 29% (~$27) - 공병: 10% (~$9) - 작전장교: 5% (~$4) - 합계: $92/월 ### 모델 비용 논의 결론 - gpt-4.1 + codex 올인 예상비용: $20~30/월 - Gemini 2.5 Pro 참모 대안 논의됨 (결국 gpt-4.1로 확정) - Anthropic Extra Usage 활성화 여부: 미결 (해병님 결정 필요) ## KAST × Movement 분석 ### 핵심 내용 - KAST: 스테이블코인 기반 글로벌 결제 플랫폼 (100만 유저, 연 $50억 거래량) - Movement 파트너십: KAST 결제 시 $MOVE 4% 캐시백 ### 토크노믹스 문제점 - 결제 → $MOVE 신규 발행 → 유저 매도 → 순 유통량 증가 - 연간 $2억어치 $MOVE 지급 (연 $50억 × 4%) - 토큰홀더 입장에서 재앙적 구조 ### Movement가 이걸 하는 이유 [score=0.810 recalls=11 avg=0.496 source=memory/2026-04-04.md:1-40]

## Promoted From Short-Term Memory (2026-04-15)

<!-- openclaw-memory-promotion:memory:memory/2026-03-20.md:64:73 -->
- - 참모(chammo): 정상 작동 확인 - 공병(ops): 정상 작동 확인 (토큰 이슈 해결됨) - 친구초대 봇(mate_ref_bot, 8715030972): 정상 - 캠페인봇(fireantagent_bot, 8184331170): 별도 운영 중 ## Eigen Cloud 메모 - AWS: 범용 클라우드, OpenClaw 셋팅에 적합 - Eigen Cloud: 검증 가능한 AI 컴퓨팅 특화 (EigenLayer 생태계) - Phala Network(PHA): 프라이버시 특화 AI 컴퓨팅, Polkadot→ETH L2 전환 완료(2025.11) [score=0.854 recalls=16 avg=0.456 source=memory/2026-03-20.md:64-73]
<!-- openclaw-memory-promotion:memory:memory/2026-04-06.md:174:195 -->
- - 3~4개월 후 재검 필요 ## 불개미 게시판 당첨자 조회 페이지 작업 (2026-04-06) - URL: https://josoyjjk-ui.github.io/fireant-dashboard/winners/ - **Eigen Cloud 친구초대 이벤트 당첨자 1,380명 추가 완료** - winners.json 총 건수: 1,734건 (Ethgas 354 + Eigen 1,380) - Eigen 데이터 형식: event, telegram, reward, points, rank 필드 포함 - 검색 시 Eigen 당첨자 카드에 "🏅 포인트: XXX점" 조건부 표시 - Ethgas 기존 데이터 완전 보존 (포인트 미표시) - 커밋 SHA: 1d76b7c2 (feat(winners): add Eigen referral winners with points/rank) - 작전장교 검증: PASS ## Eigen Cloud 배너 제작 (2026-04-06 오후) - 원본 배너: `/Users/fireant/.openclaw/media/inbound/file_282---f486abc9-af32-47fc-b1d6-d029046ff7d2.jpg` - Eigen Cloud 로고 이미지: `/Users/fireant/.openclaw/media/inbound/file_283---2a651942-5e06-4038-b810-998bfd8aad36.jpg` - 공병이 제작한 v2 배너: `/Users/fireant/.openclaw/workspace/assets/eigen-banner-v2.jpg` - 상단 Eigen Cloud 로고 유지, 불개미 크립토 로고+문구 삭제, 하단 일정 삭제 - 중앙에 "뭣?! Eigen 코인을 사면\n원금을 돌려준다고?!" 삽입 - 추가 요청: 불개미 크립토가 Eigen Cloud 코인을 소중히 바라보는 형태의 새 배너 - 문구: "뭣?! 코인을 가지고있으면 원금을 돌려준다고?!" [score=0.810 recalls=5 avg=0.529 source=memory/2026-04-06.md:174-195]
<!-- openclaw-memory-promotion:memory:memory/2026-03-12.md:55:78 -->
- - **ever_registered 버그**: register_user 함수가 등록 시 ever_registered=1 세팅 안 함 → 수정 - 기존 4명 ever_registered=1 소급 적용 - /start 시 Billions 이벤트 공지 자동 표시 추가: - 📣 Billions 채널/대화방 링크: t.me/Billions_Korea, t.me/billions_Koreachat - 채널 환영 메시지 자동 삭제: 30초 → 5초 변경 - 이벤트명 placeholder: "예: 메가이더 불개미 AMA 3월 21일 오후 8시" - commit: d0f79d5 (ever_registered 수정), 5ea0ea8 (Billions 공지) ## 친구초대봇 초기화 (23:22 KST) - 유저 전체 삭제 (4명 → 0명) - 이벤트 기간 유지: 2026-03-12 ~ 2026-04-01 ## 대시보드 리더보드 페이지 신규 추가 (23:25~23:49 KST) - URL: https://josoyjjk-ui.github.io/fireant-dashboard/leaderboard/ - 구조: referral-bot DB → export_leaderboard.py → leaderboard.json → GitHub Pages - LaunchAgent: com.fireant.referral-leaderboard-sync (1시간 간격, 이벤트 기간 내에만 실행) - export 스크립트: /Users/fireant/.openclaw/workspace/bots/referral-bot/export_leaderboard.py - 리더보드 제목: "불개미 Crypto 리더보드" - 이벤트명 표시 칸 추가 (기본값: 친구초대 이벤트) - 대시보드 nav에 🏆 리더보드 링크 추가 - 주황 참여 안내 박스 삭제 - commits: 5955c61, a30cae7, bed03e3, 1987dac ## 당첨자/리워드 페이지 기타 수정 [score=0.809 recalls=5 avg=0.525 source=memory/2026-03-12.md:55-78]

## Promoted From Short-Term Memory (2026-04-16)

<!-- openclaw-memory-promotion:memory:memory/2026-03-29.md:187:204 -->
- - 브라우저에서 발행 API 네트워크 캡처 시도 → POST 요청 캡처 실패 #### 차기 시도 경로 1. 발행 시 SE가 호출하는 API(PostWrite/PostModify) 직접 curl로 재현 2. `_imageUploader._uploadImages` / `_updateImageCompPhases` 직접 호출 3. SE 에디터 완전 재로드 후 `openFileDialog` 훅 + `uploadImagesFromFiles` 재시도 ### 크론잡 업데이트 완료 - `daily-chalk-main-event` (b1da835d): `gen_daily_report_html.py` 사용 - `daily-cb-premium-ask` (0cebaf36): `sessionTarget=isolated` ### Google Calendar 등록 - 4월 7일 오후 1시 — 디지털에셋 박상혁 기자 점심식사 ### AGENTS.md 업데이트 - 절대 규칙 #0 (완료보고 최우선) 추가 — git commit `adfd19a` - 절대 규칙 #1 (해병님 작업 떠넘기기 금지, 최소 3회 시도) 추가 — git commit `65e751de` [score=0.835 recalls=6 avg=0.521 source=memory/2026-03-29.md:187-204]
<!-- openclaw-memory-promotion:memory:memory/2026-03-18.md:12:26 -->
- - DAT: BTC+ETH 24h/72h 증감률 - Coinbase Premium: 24h/72h 증감률 - [ops] 시안 생성 파일 이력: fireant_chalkboard_4in1_mock.png → fireant_chalkboard_4in1_v2.png → fireant_chalkboard_4in1_v3_dat_eth.png → fireant_chalkboard_titles_v4.png → fireant_chalkboard_v5_with_date.png → fireant_chalkboard_v6_etf_note.png - [preference] 불개미 해병님 확정: 매일 15:00 KST에 '불개미 일일시황'을 이미지+텍스트 한 메시지로 전송. 텍스트 양식 고정: 1) BTC ETH 유출입 (BTC/ETH 값 + ETF 마지막 거래일 주석) 2) 미결제약정 추이 (BTC/ETH 24h·72h) 3) DAT 매수량 추이 (24h·72h) 4) 코인베이스 프리미엄 (현재 지수 + 24h 증감률 + 72h 증감률) + 마무리 코멘트 2문장. - [cron] 현재 15:00 자동 리포트 잡: daily-chalk-main-event (jobId: b1da835d-255b-497b-84a4-f914c62b7ee9), systemEvent 기반. - [critical_preference] 불개미 해병님 지시: 결과보고는 매우 중요. 모든 작업 완료 후 결과보고 누락 금지. 완료보고 최소 항목(작업명/변경파일/커밋SHA·푸시/실반영결과/리스크) 고정. ## 네이버 파워링크 광고 세팅 (2026-03-18 새벽) - [ads] 네이버 파워링크 캠페인 세팅 완료 (클로노드 계정, 광고계정 ID: 2466025) [score=0.829 recalls=7 avg=0.499 source=memory/2026-03-18.md:12-26]

## Promoted From Short-Term Memory (2026-04-17)

<!-- openclaw-memory-promotion:memory:memory/2026-03-11.md:39:61 -->
- - 공병: 호출형 (코드는 파일 기반이라 맥락 누적 불필요) - 상태: 해병님 최종 승인 대기 → 구현 진행 예정 ## 오후 작업 (12:30~15:21) — 시스템 장애 대응 및 에이전트 복구 ### 장애 원인 분석 및 복구 (12:30~15:21) - 전날 밤 Gateway 다운 원인: openai-codex OAuth `refresh_token_reused` 반복 → config.json 손상 → Gateway abort - **3단계 연쇄 장애**: 참모 모델 오류 → OAuth 토큰 소진 → openclaw.json 파싱 실패 ### 에이전트 설정 변경 (확정) - chammo primary: `openai-codex/gpt-5.3-codex` (fallback: gemini-3-pro-preview, claude-opus-4-6) - ops: `anthropic/claude-sonnet-4-6` (변경 없음) - 딸수(main): `anthropic/claude-sonnet-4-6` (변경 없음) - openai-codex/gpt-5.4-codex → 존재하지 않는 모델 (설정에서 제거) - 메인 fallback에서 openai-codex 제거 (딸수는 Anthropic만 사용) ### OpenAI Codex 토큰 문제 해결 - 원인: VS Code Codex와 OpenClaw가 동일 ChatGPT 계정 공유 → refresh_token rotation 충돌 - `openclaw models auth login`은 main 에이전트만 업데이트 → chammo/ops는 수동 동기화 필요 - 해결: 해병님이 VS Code 포트 1455 포워딩 후 재인증 (15:02 성공) - 토큰 만료: 2026-03-21 15:02 KST ### 재발방지대책 적용 [score=0.832 recalls=7 avg=0.497 source=memory/2026-03-11.md:39-61]
<!-- openclaw-memory-promotion:memory:memory/2026-02-21.md:24:38 -->
- - [x] GitHub Pages 배포 완료 → https://josoyjjk-ui.github.io/fireant-dashboard/ - [x] 커스텀 도메인 연결 → fireantcrypto.com (Cloudflare, $10.46/년, 만료 2027-02-21) - Cloudflare 계정: josoyjjk@gmail.com, Zone ID: 02661af28773dac0582a6d15d9fd0c1a - DNS: A x 4 (185.199.108~111.153) + CNAME www → josoyjjk-ui.github.io - HTTPS 인증서 자동 발급 대기 중 - [x] Google Form 설명란 업데이트 — OpenClaw 브라우저로 직접 편집 완료 - [x] 대시보드 이벤트 카드 기본 포맷 확정: 제목/일정/카운트다운(종료시점)/총보상+인원/참여링크/응모폼(있으면) - [x] 대시보드 헤더: "불개미 CRYPTO 게시판"으로 변경 - [x] 채널 링크 고정: TG채널/TG대화방/트위터/유튜브 (변경 지시 전까지 고정) - [x] Block Street AMA 카드 업데이트: Hedy, 2/25, NFT50+스타벅스400명 - [x] Block Street Fireweek 카드 업데이트: 2/23~27, NFT100+200만원 상품권 - [x] 인사이트 섹션: 실제 TG 포스트 3개 반영 (백악관 스테이블코인/세일러 오역/과세 유예) - [x] 인사이트 운영 규칙 변경: 자동수집 아니고 불개미 해병님이 링크 주면 최신순 3개 유지 - [x] 불개미스타일 포스트 작성: 대법원 관세 위헌 판결 + Mar-a-Lago 서밋 - [x] AI Agent 에세이 문법/오탈자 교정 [score=0.828 recalls=5 avg=0.526 source=memory/2026-02-21.md:24-38]
<!-- openclaw-memory-promotion:memory:memory/2026-03-11.md:73:90 -->
- ### 참모 모델 결정 (15:21 기준 미확정) - 해병님 확인: VS Code 재인증 목적 = 참모가 gpt-5.3-codex 쓰게 하려고 - 현실: 같은 계정 공유 구조상 VS Code 사용 시 토큰 충돌 → 재인증해도 금방 소진 - 제시한 옵션: 1. OpenClaw 전용 ChatGPT 계정 별도 생성 (근본 해결) 2. 참모 모델을 gemini로 확정 (안정성 우선) - **해병님 결정 대기 중** (아직 선택 안 함) ### SESSION-STATE 업데이트 필요 항목 - Billions 공지 3개 전송 대기 (Fireweek + AMA + 사전질문폼) — 여전히 대기 중 - fireantagent_bot 배포 대기 — 여전히 대기 중 ## 기술 메모 - Google OAuth 토큰: `/workspace/secrets/google-token.json` refresh_token으로 자동 갱신 가능 - gcloud auth 만료됨 (fireant@bridge34.com) — 재로그인 필요하지만 google-token.json으로 우회 가능 - Whisper 환경: `/workspace/whisper_env/` (torch + openai-whisper + moviepy) - 맥미니 일본/한국 구매 차이: 하드웨어 동일, 가격만 다름 (엔저 시 일본이 10-20% 저렴), 글로벌 워런티 [score=0.827 recalls=7 avg=0.480 source=memory/2026-03-11.md:73-90]
