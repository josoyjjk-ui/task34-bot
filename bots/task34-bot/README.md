# Task34 Telegram Bot

Google Calendar 기반 업무 리마인더 봇.

## 준비

1. 봇 토큰 Keychain 저장
```bash
security add-generic-password -s task34-bot-token -a task34bot -w 'YOUR_BOT_TOKEN'
```

2. 의존성 설치
```bash
cd /Users/fireant/.openclaw/workspace/bots/task34-bot
python3 -m pip install -r requirements.txt
```

3. 실행
```bash
python3 bot.py
```

## 명령어
- `/start` : 현재 그룹 활성화 (자동 리마인더 수신)
- `/today` : 오늘 일정 즉시 조회
- `/week` : 7일 일정 조회
- `/map 이메일 @username` : 담당자 매핑 등록

## LaunchAgent 등록
```bash
cp /Users/fireant/.openclaw/workspace/bots/task34-bot/com.bridge34.task34bot.plist ~/Library/LaunchAgents/com.bridge34.task34bot.plist
launchctl unload ~/Library/LaunchAgents/com.bridge34.task34bot.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.bridge34.task34bot.plist
launchctl list | grep com.bridge34.task34bot
```

## 그룹 초대 방법
1. Telegram에서 `@task34bot` 검색
2. 대상 bridge34 그룹 채팅에 봇 추가
3. 그룹에서 `/start` 실행
4. 관리자 권한에서 "메시지 보내기" 허용
