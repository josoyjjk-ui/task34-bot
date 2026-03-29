# 네이버 블로그 자동 발행 스크립트

## 파일
- `publish.py` — 삭제 + 재발행 메인 스크립트 (Playwright 기반)

## 사용법

### 기본 실행
```bash
pkill -f "Google Chrome" 2>/dev/null
sleep 2
rm -f "/Users/fireant/.openclaw/browser/openclaw/user-data/SingletonLock" 2>/dev/null
python3 publish.py
```

### 환경변수로 파라미터 교체
스크립트 상단 변수 수정:
```python
LOG_NO_DELETE = "224233588152"  # 삭제할 logNo
IMAGE_PATH = "/tmp/openclaw/uploads/daily_blog_20260329.png"  # 이미지 경로
POST_TITLE = "📌 [불개미 일일시황] 2026.03.29 (일)"
POST_TEXT = "..."
```

## 핵심 메커니즘
- **로그인**: Playwright persistent context (fireant_korea / wnFhT9)
- **이미지 업로드**: `_uploadImageByBASE64` (SmartEditor 내부 API)
- **텍스트 삽입**: `_editingService.write()`
- **발행**: `publish_btn__m9KHH` 클릭 → `.confirm_btn__WEaBq` 확인

## 주의사항
- Chrome 실행 중이면 SingletonLock 충돌 → 사전에 pkill 필요
- 캡차 발생 시 자동화 불가 → 해병님 직접 로그인 후 재시도
- 이미지는 반드시 `/tmp/openclaw/uploads/` 경로에 저장

## 알려진 이슈
- 네이버 로그인 세션 만료 주기: ~수 시간
- SmartEditor `insertNewLine` 없음 → `write()`에 `\n` 포함해서 단번에 입력
- 사진 버튼: `se-insert-menu-button-image` 클래스 클릭 → `_uploadImageByBASE64` 호출

## 의존성
```bash
pip3 install --break-system-packages playwright
python3 -m playwright install chromium
```
