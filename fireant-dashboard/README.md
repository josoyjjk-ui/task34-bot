# 🐜 FireAnt Dashboard

**FireAnt Dashboard**는 암호화폐 시장 분석, ETF 데이터 시각화, 트레이딩 리더보드, 이벤트 관리 등을 제공하는 종합 대시보드 프로젝트입니다.

## 📁 프로젝트 구조

```
fireant-dashboard/
├── index.html              # 메인 대시보드 진입점 (GitHub Pages)
├── CNAME                   # 커스텀 도메인 설정
├── leaderboard.json        # 리더보드 데이터
├── package.json            # Node.js 의존성
│
├── src/                    # 📂 소스 코드
│   ├── bots/               # 봇 관련 소스
│   ├── events/             # 이벤트 페이지
│   ├── feed/               # 피드 소스
│   ├── indicators/         # 지표 시각화
│   ├── kr-exchange/        # 한국 거래소 관련
│   ├── leaderboard/        # 리더보드 소스
│   ├── winners/            # 우수 트레이더
│   ├── fireant-todo/       # 내부 TODO 관리
│   └── *.html              # 개별 대시보드 페이지
│
├── ops/                    # 📂 운영/배포
│   ├── backtest_*.py       # 백테스트 스크립트
│   ├── etf_capture.sh      # ETF 차트 자동 캡처
│   ├── etf_image_gen.py    # ETF 이미지 생성
│   ├── fireantagent_bot.py # 텔레그램 봇
│   └── *.json              # 운영 데이터 (피드, 이벤트 등)
│
├── assets/                 # 📂 정적 에셋
│   └── *.png / *.jpg       # 배너, 로고, 프로필 이미지
│
├── docs/                   # 📂 문서
│   ├── agents/             # 에이전트 문서
│   └── memory/             # 메모리 시스템 문서
│
├── memory-system/          # 메모리 시스템 모듈
├── skills/                 # 에이전트 스킬 정의
├── proposals/              # 기능 제안서
├── secrets/                # 민감 정보 (Git 추적 제외)
├── .github/                # GitHub 설정 (Actions 등)
└── .vscode/                # VSCode 설정
```

## 🚀 배포

이 프로젝트는 **GitHub Pages**를 통해 배포됩니다.
- URL: [https://josoyjjk-ui.github.io/fireant-dashboard/](https://josoyjjk-ui.github.io/fireant-dashboard/)
- `main` 브랜치에 push되면 자동으로 배포됩니다.

## 🤝 기여 가이드

1. **브랜치 생성**: `feature/기능명` 또는 `fix/수정명` 형식으로 브랜치를 생성합니다.
2. **커밋 메시지**: [Conventional Commits](https://www.conventionalcommits.org/) 형식을 따릅니다.
   - `feat: 새로운 기능 추가`
   - `fix: 버그 수정`
   - `docs: 문서 수정`
   - `refactor: 코드 리팩토링`
3. **코드 리뷰**: PR 생성 후 리뷰를 받습니다.
4. **주의사항**:
   - `index.html`은 반드시 루트에 유지합니다.
   - 파일 이동 시 상대경로가 깨지지 않도록 확인합니다.
   - API 키나 민감 정보는 `secrets/` 디렉토리에만 저장합니다.

## 📜 라이선스

이 프로젝트는 사내/팀 내부용으로 관리됩니다.
