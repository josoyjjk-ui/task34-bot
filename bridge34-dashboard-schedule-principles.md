# bridge34.com 대시보드 일정 운영 원칙 — 5줄 요약

1. 공통 일정은 전체 화면에서 중복 없이 1회만 노출하며, 동일 date+title+event_id 조합은 dedupe 처리한다.
2. 일정 데이터는 단일 소스(normalized_schedule)에서만 렌더링하여 데이터 일관성을 보장한다.
3. 이벤트 상태는 draft→open→closed→settled 순으로 전이하며, 예약 게시 시 starts_at 도달하면 자동 활성화한다.
4. 시간은 내부 UTC로 저장하고 관리 UI는 KST로 표기하며, 상태 전환 배치 실패 시 알람을 발송한다.
5. 모든 일정 변경은 audit_logs에 기록하고, events.version 기반으로 직전 버전 롤백을 지원한다.
