# auth-state.json Cooldown 상태 보고서

✅ auth-state.json cooldown 상태 확인 완료 — 3개 모델 중 zai:default만 ~238분 cooldown 진행 중(rate_limit), 나머지 2개 정상

## 요약:
1. auth-state.json의 usageStats에 3개 모델 키 존재: zai:default는 rate_limit으로 cooldown ~238분 남음, zai:fallback과 google:default는 정상
2. lastGood 기준 현재 활성 라우팅: zai → zai:fallback, google → google:default (cooldown 모델 우회 중)
3. 파일 수정 없음 — 읽기 전용 검사 완료

## 모델별 cooldown 상태

| 모델 키 | 상태 | cooldownUntil | cooldown 사유 | errorCount | cooldownModel |
|---|---|---|---|---|---|
| zai:default | 🔴 cooldown ~238분 남음 | 1776418921301 | rate_limit | 1 | glm-5.1 |
| zai:fallback | ✅ 정상 | 0 (없음) | - | 0 | - |
| google:default | ✅ 정상 | 0 (없음) | - | 0 | - |

## lastGood (현재 활성 라우팅)
- zai → zai:fallback (cooldown 우회)
- google → google:default

## zai:default 상세
- cooldownReason: rate_limit
- cooldownModel: glm-5.1
- failureCounts: { "rate_limit": 1 }
- cooldown 만료 예상: 현재로부터 약 238분(~4시간) 후

## 변경 파일: 없음
## 실행한 테스트: auth-state.json 읽기 및 파싱, cooldown 잔여 시간 계산
## 경고: zai:default가 glm-5.1 모델 rate_limit으로 인해 약 4시간 cooldown 중. 현재 zai:fallback으로 정상 우회됨.
